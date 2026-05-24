"""
VERA Office - Developer Review Queue API
Boris' Requirement: "Wenn VERA gar nicht weiterkommt, 
                     muss VERA das Entwickler-Team fragen"

WORKFLOW:
1. User + VERA unsicher → Dokument in Developer Queue
2. Developer öffnet Queue
3. Developer reviewt Dokument
4. Developer entscheidet:
   - Neue Kategorie erstellen
   - Regel hinzufügen
   - OCR-Problem markieren
   - Training nötig
5. System-Update → Alle Praxen profitieren
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

from backend.db.database import get_db
from backend.models.document import Document
from backend.core.ai.dynamic_categories import dynamic_categories

router = APIRouter(prefix="/dev-queue", tags=["Developer Queue"])


# ============================================================
# Models
# ============================================================

class DevQueueItem(BaseModel):
    """Document in developer review queue"""
    id: int
    filename: str
    ocr_text: Optional[str]
    user_comment: Optional[str]
    escalated_by: Optional[str]
    escalated_at: Optional[str]
    confidence: Optional[float]


class DevReviewRequest(BaseModel):
    """Developer's review decision"""
    doc_id: int
    decision: str  # "new_category" | "add_rule" | "ocr_problem" | "needs_training"
    category: Optional[str] = None
    explanation: Optional[str] = None
    notes: Optional[str] = None


class DevReviewResponse(BaseModel):
    """Review confirmation"""
    status: str
    message: str
    category: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.get("/queue", response_model=List[DevQueueItem])
async def get_developer_queue(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all documents waiting for developer review.
    
    Returns:
        List of documents with status "needs_dev_review"
    """
    docs = db.query(Document).filter(
        Document.classification_status == "needs_dev_review"
    ).order_by(
        Document.escalated_at.desc()
    ).limit(limit).all()
    
    queue_items = []
    for doc in docs:
        queue_items.append(DevQueueItem(
            id=doc.id,
            filename=doc.filename,
            ocr_text=doc.ocr_text[:500] if doc.ocr_text else None,  # Truncate for preview
            user_comment=doc.user_comment,
            escalated_by=doc.escalated_by,
            escalated_at=doc.escalated_at.isoformat() if doc.escalated_at else None,
            confidence=doc.confidence
        ))
    
    logger.info(f"[DevQueue] Loaded {len(queue_items)} items")
    
    return queue_items


@router.post("/review", response_model=DevReviewResponse)
async def review_document(
    request: DevReviewRequest,
    db: Session = Depends(get_db)
):
    """
    Developer reviews document and makes decision.
    
    Decisions:
    - new_category: Create new category + update system
    - add_rule: Add classification rule
    - ocr_problem: Mark as OCR quality issue
    - needs_training: Mark for additional training data
    """
    # Get document
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.classification_status != "needs_dev_review":
        raise HTTPException(
            status_code=400,
            detail="Document is not in developer review queue"
        )
    
    # Process decision
    if request.decision == "new_category":
        # Developer creates new category
        if not request.category or not request.explanation:
            raise HTTPException(
                status_code=400,
                detail="new_category requires category and explanation"
            )
        
        # Extract category info from developer's explanation
        category_info = dynamic_categories.extract_category_from_explanation(
            request.explanation
        )
        
        # Use provided category name if different
        if request.category:
            category_info["full_name"] = request.category
            category_info["main"] = request.category
        
        # Add category (user_id=0 for system/developer)
        result = dynamic_categories.add_new_category(
            category_info,
            user_id=0,
            user_name="Developer"
        )
        
        # Update document
        doc.category = category_info["full_name"]
        doc.confidence = 1.0
        doc.classification_status = "dev_reviewed"
        doc.reviewed_at = datetime.now()
        doc.dev_notes = request.notes
        db.commit()
        
        logger.info(
            f"[DevQueue] ✓ New category created by dev: "
            f"'{category_info['full_name']}' for doc {doc.id}"
        )
        
        return DevReviewResponse(
            status="reviewed",
            message=f"Neue Kategorie '{category_info['full_name']}' erstellt",
            category=category_info["full_name"]
        )
    
    elif request.decision == "add_rule":
        # Developer adds classification rule
        # TODO: Implement rule addition system
        
        doc.classification_status = "dev_reviewed"
        doc.reviewed_at = datetime.now()
        doc.dev_notes = f"Rule added: {request.notes}"
        db.commit()
        
        logger.info(f"[DevQueue] ✓ Rule added for doc {doc.id}")
        
        return DevReviewResponse(
            status="reviewed",
            message="Regel hinzugefügt"
        )
    
    elif request.decision == "ocr_problem":
        # Mark as OCR quality issue
        doc.classification_status = "ocr_problem"
        doc.reviewed_at = datetime.now()
        doc.dev_notes = f"OCR Issue: {request.notes}"
        db.commit()
        
        logger.warning(f"[DevQueue] ⚠ OCR problem marked for doc {doc.id}")
        
        return DevReviewResponse(
            status="reviewed",
            message="Als OCR-Problem markiert"
        )
    
    elif request.decision == "needs_training":
        # Mark for training data collection
        doc.classification_status = "training_data"
        doc.reviewed_at = datetime.now()
        doc.dev_notes = f"Training needed: {request.notes}"
        db.commit()
        
        logger.info(f"[DevQueue] ✓ Marked for training: doc {doc.id}")
        
        return DevReviewResponse(
            status="reviewed",
            message="Als Training-Daten markiert"
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision: {request.decision}"
        )


@router.get("/stats")
async def get_dev_queue_stats(
    db: Session = Depends(get_db)
):
    """
    Developer queue statistics.
    
    Returns:
        - Total items in queue
        - Oldest item
        - Average wait time
        - Items by escalation reason
    """
    # Count items
    total_in_queue = db.query(Document).filter(
        Document.classification_status == "needs_dev_review"
    ).count()
    
    # Get oldest item
    oldest = db.query(Document).filter(
        Document.classification_status == "needs_dev_review"
    ).order_by(Document.escalated_at.asc()).first()
    
    # Items reviewed
    reviewed = db.query(Document).filter(
        Document.classification_status == "dev_reviewed"
    ).count()
    
    # OCR problems
    ocr_problems = db.query(Document).filter(
        Document.classification_status == "ocr_problem"
    ).count()
    
    return {
        "total_in_queue": total_in_queue,
        "total_reviewed": reviewed,
        "total_ocr_problems": ocr_problems,
        "oldest_item": {
            "id": oldest.id if oldest else None,
            "filename": oldest.filename if oldest else None,
            "escalated_at": oldest.escalated_at.isoformat() if oldest and oldest.escalated_at else None
        } if oldest else None
    }


@router.delete("/{doc_id}")
async def remove_from_queue(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove document from developer queue (mark as resolved).
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.classification_status != "needs_dev_review":
        raise HTTPException(
            status_code=400,
            detail="Document is not in developer queue"
        )
    
    # Mark as resolved without action
    doc.classification_status = "dev_skipped"
    doc.reviewed_at = datetime.now()
    db.commit()
    
    logger.info(f"[DevQueue] Document {doc_id} removed from queue")
    
    return {"status": "removed", "doc_id": doc_id}
