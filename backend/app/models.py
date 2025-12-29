from pydantic import BaseModel
from uuid import UUID
from typing import List, Dict, Optional
from datetime import datetime

class TranscriptTurn(BaseModel):
    role: str
    content: str
    timestamp: float
    latency: float

class FreezeEvent(BaseModel):
    start_time: float
    end_time: float
    duration: float

class Session(BaseModel):
    id: str | UUID
    created_at: datetime
    transcript: List[TranscriptTurn]
    freeze_events: List[FreezeEvent]
    latency_metrics: Dict[str, float]
    audio_url: Optional[str]