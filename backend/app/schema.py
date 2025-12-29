from sqlmodel import SQLModel, Field, Column, JSON
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID, uuid4

class Session(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    transcript: List[dict] = Field(default=[], sa_column=Column(JSON))
    freeze_events: List[dict] = Field(default=[], sa_column=Column(JSON))
    latency_metrics: Dict[str, float] = Field(default={}, sa_column=Column(JSON))
    audio_url: Optional[str] = None
