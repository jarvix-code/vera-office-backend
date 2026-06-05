"""
VERA Office - Calendar API
Endpunkte für das Kalender-Modul im Frontend.
Liefert /api/calendar/events (GET), /api/calendar/events/{id} (GET),
/api/calendar/events (POST), /api/calendar/events/{id} (PATCH),
/api/calendar/events/{id} (DELETE).

Bug #1181: Frontend ruft /api/calendar/events — Route fehlte komplett.
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from pydantic import BaseModel
from typing import List, Optional

from backend.db.database import get_db, Base

router = APIRouter()


# ── ORM Model ─────────────────────────────────────────────────────────────────

class CalendarEvent(Base):
    """SQLAlchemy-Modell für Kalendertermine."""
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    event_date = Column(String(20), nullable=False)   # ISO date string: YYYY-MM-DD
    event_time = Column(String(10), nullable=False, default="00:00")  # HH:MM
    duration = Column(String(50), nullable=False, default="1h")
    type = Column(String(20), nullable=False, default="task")  # meeting|task|deadline
    deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class CalendarEventOut(BaseModel):
    """Kalender-Termin wie vom Frontend erwartet (ModuleView.tsx KalenderView)."""
    id: str
    title: str
    date: str
    time: str
    duration: str
    type: str

    class Config:
        from_attributes = True


class CalendarEventsResponse(BaseModel):
    events: List[CalendarEventOut]


class CalendarEventCreate(BaseModel):
    title: str
    date: str
    time: str = "00:00"
    duration: str = "1h"
    type: str = "task"


class CalendarEventPatch(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[str] = None
    type: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _event_to_out(ev: CalendarEvent) -> CalendarEventOut:
    return CalendarEventOut(
        id=str(ev.id),
        title=ev.title,
        date=ev.event_date,
        time=ev.event_time,
        duration=ev.duration,
        type=ev.type,
    )


def _ensure_table(db: Session):
    """Stellt sicher dass die calendar_events Tabelle existiert (lazy migration)."""
    from backend.db.database import engine
    CalendarEvent.__table__.create(bind=engine, checkfirst=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/events", response_model=CalendarEventsResponse, tags=["Calendar"])
async def list_events(db: Session = Depends(get_db)):
    """
    GET /api/calendar/events
    Liefert alle nicht-gelöschten Kalendertermine aufsteigend nach Datum.
    """
    _ensure_table(db)
    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.deleted == False)
        .order_by(CalendarEvent.event_date, CalendarEvent.event_time)
        .all()
    )
    return CalendarEventsResponse(events=[_event_to_out(e) for e in events])


@router.get("/events/{event_id}", response_model=CalendarEventOut, tags=["Calendar"])
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """GET /api/calendar/events/{id} — Einzelnen Termin abrufen."""
    _ensure_table(db)
    ev = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.deleted == False
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Termin {event_id} nicht gefunden")
    return _event_to_out(ev)


@router.post("/events", response_model=CalendarEventOut, status_code=201, tags=["Calendar"])
async def create_event(data: CalendarEventCreate, db: Session = Depends(get_db)):
    """POST /api/calendar/events — Neuen Termin anlegen."""
    _ensure_table(db)
    ev = CalendarEvent(
        title=data.title,
        event_date=data.date,
        event_time=data.time,
        duration=data.duration,
        type=data.type,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return _event_to_out(ev)


@router.patch("/events/{event_id}", response_model=CalendarEventOut, tags=["Calendar"])
async def patch_event(
    event_id: int, patch: CalendarEventPatch, db: Session = Depends(get_db)
):
    """PATCH /api/calendar/events/{id} — Termin aktualisieren."""
    _ensure_table(db)
    ev = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.deleted == False
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Termin {event_id} nicht gefunden")
    if patch.title is not None:
        ev.title = patch.title
    if patch.date is not None:
        ev.event_date = patch.date
    if patch.time is not None:
        ev.event_time = patch.time
    if patch.duration is not None:
        ev.duration = patch.duration
    if patch.type is not None:
        ev.type = patch.type
    db.commit()
    db.refresh(ev)
    return _event_to_out(ev)


@router.delete("/events/{event_id}", status_code=204, tags=["Calendar"])
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """DELETE /api/calendar/events/{id} — Termin (soft-delete)."""
    _ensure_table(db)
    ev = db.query(CalendarEvent).filter(
        CalendarEvent.id == event_id, CalendarEvent.deleted == False
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail=f"Termin {event_id} nicht gefunden")
    ev.deleted = True
    db.commit()
