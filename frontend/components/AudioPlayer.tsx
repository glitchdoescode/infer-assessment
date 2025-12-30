"use client";

import { useEffect, useRef, useState } from "react";
import { TranscriptTurn } from "../lib/api";
import { Play, Pause, RotateCcw } from "lucide-react";

interface AudioPlayerProps {
    src?: string;
    transcript: TranscriptTurn[];
    onTimeUpdate?: (currentTime: number) => void;
}

export function AudioPlayer({ src, transcript, onTimeUpdate }: AudioPlayerProps) {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

    // Filter assistant turns with latency
    const assistantTurns = transcript.filter(
        (turn) => turn.role === "assistant" && turn.latency > 0
    );

    // Find the first timestamp to normalize visual timeline if needed
    // But usually audio starts at 0. 
    // Timestamps in transcript are absolute UTC. 
    // We need to map them to relative audio time.
    // Assumption: The first turn corresponds to start of audio? 
    // No, actually recordings might be one continuous file or chunks.
    // The 'timestamp' in transcript is wall clock.
    // We need to know the start time of the recording to map wall clock to audio time.
    // The session 'created_at' is likely the start time.
    // BUT: bot.py starts recording on client_connected.
    // Session created_at is set when session_data is init.
    // Timestamps are set when messages arrive.
    // We can approximate: start_time = first turn timestamp if user spoke first?
    // Let's assume start_time is roughly the first timestamp.
    const startTime = transcript.length > 0 ? transcript[0].timestamp : 0;

    // Actually, we need to be careful. The audio file starts from 0s. 
    // The transcript timestamps are absolute numbers.
    // Relative offset = turn.timestamp - startTime.

    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            const time = audioRef.current.currentTime;
            setCurrentTime(time);
            if (onTimeUpdate) {
                onTimeUpdate(time);
            }
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const formatTime = (time: number) => {
        const minutes = Math.floor(time / 60);
        const seconds = Math.floor(time % 60);
        return `${minutes}:${seconds.toString().padStart(2, "0")}`;
    };

    if (!src) return <div className="text-gray-500">No audio recording available</div>;

    return (
        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-100">
            <audio
                ref={audioRef}
                src={src}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={() => setIsPlaying(false)}
            />

            {/* Controls */}
            <div className="flex items-center gap-4 mb-4">
                <button
                    onClick={togglePlay}
                    className="w-10 h-10 flex items-center justify-center rounded-full bg-blue-600 text-white hover:bg-blue-700 transition"
                >
                    {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-1" />}
                </button>
                <div className="text-sm font-medium text-gray-600">
                    {formatTime(currentTime)} / {formatTime(duration)}
                </div>
            </div>

            {/* Timeline / Visualization */}
            <div className="relative h-12 bg-gray-50 rounded select-none cursor-pointer"
                onClick={(e) => {
                    if (!audioRef.current) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    const pos = (e.clientX - rect.left) / rect.width;
                    audioRef.current.currentTime = pos * duration;
                }}>

                {/* Progress Bar */}
                <div
                    className="absolute top-0 left-0 h-full bg-blue-100 rounded opacity-50"
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                />

                {/* Scrubber Line */}
                <div
                    className="absolute top-0 h-full w-0.5 bg-blue-600 z-10 control-none pointer-events-none"
                    style={{ left: `${(currentTime / duration) * 100}%` }}
                />

                {/* Latency Markers */}
                {assistantTurns.map((turn, i) => {
                    const relativeTime = turn.timestamp - startTime;
                    // Only show if within duration
                    if (relativeTime < 0 || relativeTime > duration) return null;

                    const position = (relativeTime / duration) * 100;

                    return (
                        <div
                            key={i}
                            className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-amber-400 group cursor-help z-20 flex items-center justify-center border border-white shadow-sm"
                            style={{ left: `${position}%` }}
                            title={`Latency: ${turn.latency.toFixed(2)}s`}
                        >
                            <div className="hidden group-hover:block absolute bottom-full mb-1 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-30">
                                {turn.latency.toFixed(2)}s
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-2 text-xs text-gray-400 flex justify-between">
                <span>0:00</span>
                <span>Latency events marked in yellow</span>
                <span>{formatTime(duration)}</span>
            </div>
        </div>
    );
}
