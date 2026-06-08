"""
Inbox Batch Processor API
Verarbeitet alle existierenden Dateien in Inbox (manuelle Trigger-Alternative zu Hotfolder-Scanner)
"""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.api.auth import get_current_user
from backend.models.user import User
from pydantic import BaseModel
from typing import List
from pathlib import Path
import asyncio
import uuid
from loguru import logger

from backend.config import config

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

# In-memory job tracking
_jobs = {}

class InboxProcessResponse(BaseModel):
    job_id: str
    total_files: int
    message: str

class InboxProcessProgress(BaseModel):
    job_id: str
    status: str  # "running" | "done" | "error"
    total: int
    done: int
    errors: int
    current_file: str | None

async def _process_inbox_batch(job_id: str):
    """Background Task: Verarbeitet alle Inbox-Dateien"""
    from backend.main import process_new_document
    
    job = _jobs[job_id]
    inbox_path = config.INBOX_DIR
    
    # Finde alle verarbeitbaren Dateien
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    files = [
        f for f in inbox_path.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_extensions
    ]
    
    job["total"] = len(files)
    logger.info(f"[BATCH {job_id}] Starte Verarbeitung von {len(files)} Dateien...")
    
    for i, file_path in enumerate(files):
        job["current_file"] = file_path.name
        try:
            await process_new_document(file_path)
            job["done"] = i + 1
            logger.debug(f"  [{i+1}/{len(files)}] {file_path.name} verarbeitet")
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei {file_path.name}: {e}")
            job["errors"] += 1
            job["done"] = i + 1
    
    job["status"] = "done"
    job["current_file"] = None
    logger.success(f"[OK] Batch {job_id} abgeschlossen: {job['done']}/{job['total']} ({job['errors']} Fehler)")

@router.post("/process-all", response_model=InboxProcessResponse, dependencies=[])
async def process_all_inbox(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """
    Verarbeitet alle existierenden Dateien in Inbox (PDF, JPG, PNG)
    Alternative zum Hotfolder-Scanner für bereits vorliegende Dateien
    """
    inbox_path = config.INBOX_DIR
    
    # Zähle Dateien
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    files = [
        f for f in inbox_path.iterdir()
        if f.is_file() and f.suffix.lower() in allowed_extensions
    ]
    
    if not files:
        return InboxProcessResponse(
            job_id="none",
            total_files=0,
            message="Keine Dateien in Inbox gefunden"
        )
    
    # Erstelle Job
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "status": "running",
        "total": 0,  # Wird in Background Task gesetzt
        "done": 0,
        "errors": 0,
        "current_file": None
    }
    
    # Starte Background Processing
    background_tasks.add_task(_process_inbox_batch, job_id)
    
    return InboxProcessResponse(
        job_id=job_id,
        total_files=len(files),
        message=f"{len(files)} Dateien werden verarbeitet..."
    )

@router.get("/process-progress/{job_id}", response_model=InboxProcessProgress)
async def get_process_progress(job_id: str):
    """Gibt Fortschritt der Batch-Verarbeitung zurück"""
    if job_id not in _jobs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    job = _jobs[job_id]
    return InboxProcessProgress(job_id=job_id, **job)


@router.get("/unprocessed")
async def get_unprocessed(current_user: User = Depends(get_current_user)):
    """Gibt unverarbeitete Dateien in inbox zurück"""
    inbox_path = config.INBOX_DIR
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    try:
        files = [
            {"filename": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime}
            for f in inbox_path.iterdir()
            if f.is_file() and f.suffix.lower() in allowed_extensions
        ]
    except Exception:
        files = []
    return {"files": files, "count": len(files)}


@router.get("/stats")
async def get_inbox_stats(current_user: User = Depends(get_current_user)):
    """Gibt Inbox-Statistiken zurück"""
    inbox_path = config.INBOX_DIR
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    try:
        files = [f for f in inbox_path.iterdir() if f.is_file() and f.suffix.lower() in allowed_extensions]
        pending = len(files)
    except Exception:
        pending = 0
    try:
        from backend.db.database import SessionLocal
        from backend.models.document import Document
        from datetime import date
        db = SessionLocal()
        today = date.today().isoformat()
        processed_today = db.query(Document).filter(Document.created_at >= today).count()
        db.close()
    except Exception:
        processed_today = 0
    return {"pending": pending, "processed_today": processed_today, "total_processed": processed_today}
