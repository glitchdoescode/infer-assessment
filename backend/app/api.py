from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session as get_db_session
from app.schema import Session as SessionModel
from app.crud import create_session, get_session as get_session_by_id, update_session
from app.models import TranscriptTurn, FreezeEvent
from uuid import UUID

router = APIRouter()

@router.post("/sessions/", response_model=SessionModel)
def create_new_session(session: SessionModel, db: Session = Depends(get_db_session)):
    return create_session(db, session)

@router.get("/sessions/{session_id}", response_model=SessionModel)
def read_session(session_id: UUID, db: Session = Depends(get_db_session)):
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/sessions/{session_id}/transcript", response_model=SessionModel)
def update_transcript(session_id: UUID, transcript: List[TranscriptTurn], db: Session = Depends(get_db_session)):
    transcript_data = [t.model_dump() for t in transcript]
    updated = update_session(db, session_id, {"transcript": transcript_data})
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated

@router.patch("/sessions/{session_id}/freeze_events", response_model=SessionModel)
def update_freeze_events(session_id: UUID, freeze_events: List[FreezeEvent], db: Session = Depends(get_db_session)):
    events_data = [e.model_dump() for e in freeze_events]
    updated = update_session(db, session_id, {"freeze_events": events_data})
    if not updated:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated
