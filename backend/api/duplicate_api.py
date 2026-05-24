"""
VERA Office - Duplicate Confirmation API
API for VERA to handle duplicate document confirmations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from backend.core.duplicate_handler import (
    get_pending_duplicate,
    resolve_duplicate,
    DuplicateDecision,
    _pending_duplicates
)
from loguru import logger

router = APIRouter()


class PendingDuplicateResponse(BaseModel):
    confirmation_id: str
    filename: str
    existing_filename: str
    existing_doc_id: int
    created_at: str
    status: str


class DuplicateConfirmRequest(BaseModel):
    confirmation_id: str
    decision: str  # skip, compare, delete_old, keep_both


@router.get("/duplicates/pending", response_model=List[PendingDuplicateResponse])
async def list_pending_duplicates():
    """List all pending duplicate confirmations."""
    pending = []
    
    for conf_id, data in _pending_duplicates.items():
        if data["status"] == "pending":
            pending.append(PendingDuplicateResponse(
                confirmation_id=conf_id,
                filename=data["file_path"].split("/")[-1],
                existing_filename=data["existing_doc_filename"],
                existing_doc_id=data["existing_doc_id"],
                created_at=data["created_at"],
                status=data["status"]
            ))
    
    return pending


@router.post("/duplicates/confirm")
async def confirm_duplicate(request: DuplicateConfirmRequest):
    """
    Confirm duplicate handling decision.
    
    Actions:
    - skip: Delete new document
    - compare: Open comparison view (future)
    - delete_old: Delete old document, keep new
    - keep_both: Keep both documents
    """
    pending = get_pending_duplicate(request.confirmation_id)
    
    if not pending:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    
    if pending["status"] != "pending":
        raise HTTPException(status_code=400, detail="Already resolved")
    
    # Resolve
    resolve_duplicate(request.confirmation_id, request.decision)
    
    # Execute action based on decision
    from pathlib import Path
    from backend.config import config
    from backend.db.database import SessionLocal
    from backend.models.document import Document
    
    pending_file = Path(pending["file_path"])
    db = SessionLocal()
    
    try:
        if request.decision == DuplicateDecision.SKIP:
            # Delete new document
            if pending_file.exists():
                pending_file.unlink()
            logger.info(f"Duplicate skipped: {pending_file.name}")
            message = "[OK] Neues Dokument übersprungen"
            
        elif request.decision == DuplicateDecision.DELETE_OLD:
            # Delete old document from DB and filesystem
            existing_doc = db.query(Document).get(pending["existing_doc_id"])
            if existing_doc:
                # Delete file
                doc_path = config.DOCUMENTS_DIR / existing_doc.filename
                if doc_path.exists():
                    doc_path.unlink()
                
                # Delete DB entry
                db.delete(existing_doc)
                db.commit()
            
            # Resume processing of new document
            # Move back to inbox
            inbox_dir = config.DATA_DIR / "inbox"
            inbox_file = inbox_dir / pending_file.name
            pending_file.rename(inbox_file)
            
            logger.info(f"Old document deleted, processing new: {pending_file.name}")
            message = "[OK] Altes Dokument gelöscht, neues wird verarbeitet"
            
        elif request.decision == DuplicateDecision.KEEP_BOTH:
            # Resume processing of new document
            inbox_dir = config.DATA_DIR / "inbox"
            inbox_file = inbox_dir / pending_file.name
            pending_file.rename(inbox_file)
            
            logger.info(f"Keeping both documents: {pending_file.name}")
            message = "[OK] Beide Dokumente werden behalten"
            
        elif request.decision == DuplicateDecision.COMPARE:
            # TODO: Implement comparison view
            message = "[SEARCH] Vergleichsansicht noch nicht implementiert"
        
        else:
            raise HTTPException(status_code=400, detail="Invalid decision")
        
        return {
            "success": True,
            "message": message,
            "confirmation_id": request.confirmation_id
        }
        
    finally:
        db.close()
