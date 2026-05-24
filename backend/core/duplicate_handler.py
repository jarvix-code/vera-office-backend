"""
VERA Office - Duplicate Handler
Handles duplicate document detection and user confirmation.
"""
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import uuid

from backend.models.document import Document
from loguru import logger

# In-memory pending duplicates (production: use Redis)
_pending_duplicates: Dict[str, dict] = {}


class DuplicateDecision:
    """User decision for duplicate handling."""
    SKIP = "skip"
    COMPARE = "compare"
    DELETE_OLD = "delete_old"
    KEEP_BOTH = "keep_both"


def check_duplicate(ocr_text: str, db) -> Optional[Document]:
    """
    Check if OCR text matches an existing document.
    
    Returns:
        Document if duplicate found, None otherwise
    """
    if not ocr_text or len(ocr_text) < 100:
        return None
    
    # Search for similar documents (first 500 chars)
    text_preview = ocr_text[:500]
    existing_docs = db.query(Document).filter(
        Document.ocr_text.isnot(None)
    ).all()
    
    for existing in existing_docs:
        if not existing.ocr_text or len(existing.ocr_text) < 100:
            continue
        
        # Calculate word-overlap similarity
        words_new = set(text_preview.lower().split())
        words_existing = set(existing.ocr_text[:500].lower().split())
        
        if len(words_new) == 0:
            continue
        
        similarity = len(words_new & words_existing) / len(words_new)
        
        if similarity > 0.7:  # 70% match = duplicate
            logger.info(f"Duplicate found: {existing.filename} (similarity: {similarity:.0%})")
            return existing
    
    return None


def create_pending_duplicate(file_path: Path, ocr_text: str, existing_doc: Document) -> str:
    """
    Creates a pending duplicate confirmation request.
    
    Returns:
        Confirmation ID for user response
    """
    confirmation_id = str(uuid.uuid4())[:8]
    
    _pending_duplicates[confirmation_id] = {
        "file_path": str(file_path),
        "ocr_text": ocr_text,
        "existing_doc_id": existing_doc.id,
        "existing_doc_filename": existing_doc.filename,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    }
    
    logger.info(f"Created duplicate confirmation request: {confirmation_id}")
    return confirmation_id


def get_pending_duplicate(confirmation_id: str) -> Optional[dict]:
    """Get pending duplicate by ID."""
    return _pending_duplicates.get(confirmation_id)


def resolve_duplicate(confirmation_id: str, decision: str) -> bool:
    """
    Resolve a pending duplicate with user decision.
    
    Args:
        confirmation_id: Confirmation ID
        decision: One of DuplicateDecision values
    
    Returns:
        True if resolved, False if not found
    """
    if confirmation_id not in _pending_duplicates:
        return False
    
    pending = _pending_duplicates[confirmation_id]
    pending["status"] = "resolved"
    pending["decision"] = decision
    pending["resolved_at"] = datetime.now().isoformat()
    
    logger.info(f"Duplicate {confirmation_id} resolved: {decision}")
    
    # Cleanup after 5 minutes (or process immediately)
    # For now: just mark as resolved
    return True


def get_duplicate_notification(existing_doc: Document) -> dict:
    """
    Generate notification message for VERA.
    
    Returns:
        Dict with message and action buttons
    """
    return {
        "message": f"[WARNING] **Duplikat erkannt!**\n\n"
                   f"Dieses Dokument ähnelt stark: **{existing_doc.filename}**\n\n"
                   f"Was möchtest du tun?",
        "actions": [
            {"label": "[ERROR] Überspringen", "action": "skip"},
            {"label": "[SEARCH] Vergleichen", "action": "compare"},
            {"label": " Altes löschen", "action": "delete_old"},
            {"label": "[OK] Beide behalten", "action": "keep_both"}
        ]
    }
