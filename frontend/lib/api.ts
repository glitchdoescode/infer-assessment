export interface TranscriptTurn {
    role: "user" | "assistant";
    content: string;
    timestamp: number;
    latency: number;
}

export interface FreezeEvent {
    start_time: number;
    end_time: number;
    duration: number;
}

export interface Session {
    id: string;
    created_at: string;
    transcript: TranscriptTurn[];
    freeze_events: FreezeEvent[];
    latency_metrics: {
        average_latency?: number;
        [key: string]: number | undefined;
    };
    audio_url?: string;
}

const API_BASE_URL = "http://localhost:8000/api";
const RECORDING_BASE_URL = "http://localhost:8000";

export async function fetchSessions(): Promise<Session[]> {
    const res = await fetch(`${API_BASE_URL}/sessions/`);
    if (!res.ok) {
        throw new Error("Failed to fetch sessions");
    }
    return res.json();
}

export async function fetchSession(id: string): Promise<Session> {
    const res = await fetch(`${API_BASE_URL}/sessions/${id}`);
    if (!res.ok) {
        throw new Error("Failed to fetch session");
    }
    const session = await res.json();

    // Normalize audio URL to be absolute
    if (session.audio_url && session.audio_url.startsWith("/")) {
        session.audio_url = `${RECORDING_BASE_URL}${session.audio_url}`;
    }

    return session;
}
