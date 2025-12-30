import asyncio
import os
import sys
import aiohttp
import time

from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.aggregators.llm_response import LLMUserContextAggregator, LLMAssistantContextAggregator
from pipecat.processors.aggregators.llm_context import LLMContext

from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import TextFrame, LLMFullResponseEndFrame, Frame, TranscriptionFrame, AudioRawFrame
import wave

class WavAudioRecorder(FrameProcessor):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename
        self._wav_file = None

    async def start_recording(self):
        self._wav_file = wave.open(self.filename, "wb")
        self._wav_file.setnchannels(1)
        self._wav_file.setsampwidth(2) # 16-bit
        self._wav_file.setframerate(16000) 

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await self.push_frame(frame, direction)
        if isinstance(frame, AudioRawFrame):
            if not self._wav_file:
                 await self.start_recording()
            self._wav_file.writeframes(frame.audio)

    async def cleanup(self):
        if self._wav_file:
            self._wav_file.close()
            print(f"Saved recording to {self.filename}")

from dotenv import load_dotenv

load_dotenv()

class APILogger:
    def __init__(self, api_url):
        self.api_url = api_url
        self.session_id = None
        self.start_time = time.time()

    async def create_session(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/sessions/") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.session_id = data["id"]
                    self.start_time = time.time()
                    print(f"Session created: {self.session_id}")

    async def log_transcript(self, role, content):
        if not self.session_id: return
        timestamp = time.time() - self.start_time
        payload = [{"role": role, "content": content, "timestamp": timestamp, "latency": 0.0}]
        async with aiohttp.ClientSession() as session:
            await session.patch(f"{self.api_url}/sessions/{self.session_id}/transcript", json=payload)

    async def log_freeze(self, start, end):
        if not self.session_id: return
        payload = [{"start_time": start - self.start_time, "end_time": end - self.start_time, "duration": end - start}]
        async with aiohttp.ClientSession() as session:
            await session.patch(f"{self.api_url}/sessions/{self.session_id}/freeze_events", json=payload)

class TranscriptProcessor(FrameProcessor):
    def __init__(self, logger: APILogger):
        super().__init__()
        self.logger = logger

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await self.push_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
             await self.logger.log_transcript("user", frame.text)
        elif isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
             await self.logger.log_transcript("assistant", frame.text)

class FreezeProcessor(FrameProcessor):
    def __init__(self, logger: APILogger):
        super().__init__()
        self.logger = logger
        self._frozen = False
        self._freeze_start = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if self._frozen and isinstance(frame, (TextFrame, LLMFullResponseEndFrame)):
            return
        await self.push_frame(frame, direction)

    async def set_frozen(self, frozen: bool):
        if frozen and not self._frozen:
            self._frozen = True
            self._freeze_start = time.time()
            print("Packet freeze simulated")
        elif not frozen and self._frozen:
            self._frozen = False
            await self.logger.log_freeze(self._freeze_start, time.time())
            print("Packet freeze ended")



async def simulate_freeze(processor):
    while True:
        await asyncio.sleep(20)
        await processor.set_frozen(True)
        await asyncio.sleep(5)
        await processor.set_frozen(False)

async def main():
    transport = DailyTransport(
        room_url=os.getenv("DAILY_SAMPLE_ROOM_URL"),
        token=os.getenv("DAILY_SAMPLE_ROOM_TOKEN"),
        bot_name="FreezeBot",
            audio_out_enabled=True,
            audio_in_enabled=True,
            vad_analyzer=SileroVADAnalyzer()
    )

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    
    llm = GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model="models/gemini-2.5-flash" 
    )

    logger = APILogger("http://localhost:8000/api")
    await logger.create_session()

    freeze_processor = FreezeProcessor(logger)
    transcript_processor = TranscriptProcessor(logger)

    # Recording Setup
    if not os.path.exists("backend/recordings"):
        os.makedirs("backend/recordings", exist_ok=True)
    rec_filename = f"backend/recordings/{logger.session_id}.wav"
    recorder = WavAudioRecorder(rec_filename)
    print(f"Recording to: {rec_filename}")

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="248be419-3632-4f38-9bed-683592322bd8", 
    )

    messages = [
        {
            "role": "system", 
            "content": "You are a helpful and concise voice assistant. You are testing a system that might freeze."
        }
    ]
    context = LLMContext(messages)
    user_aggregator = LLMUserContextAggregator(context)
    assistant_aggregator = LLMAssistantContextAggregator(context)

    pipeline = Pipeline([
        transport.input(),
        recorder, # Capture raw audio input
        stt,
        transcript_processor,
        user_aggregator,
        llm,
        freeze_processor,
        tts,
        transport.output(),
        assistant_aggregator
    ])

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    runner = PipelineRunner()

    asyncio.create_task(simulate_freeze(freeze_processor))

    print("Bot is connecting to Daily room...")
    
    try:
        await runner.run(task)
    finally:
        await recorder.cleanup()
    
    print("Bot disconnected.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
