"""
VERA Office - Active Learning API
Boris' Workflow: VERA fragt User bei Unsicherheit

WORKFLOW:
1. Dokument klassifiziert → Confidence < 85%
2. VERA fragt: "Hey {user}, was ist das?"
3. User kann Dokument ansehen (Reader-View)
4. User gibt FREIE Erklärung (KEINE Dropdowns!)
5. VERA extrahiert Kategorie dynamisch
6. VERA lernt + bestätigt
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.user import User
from backend.core.ai.safe_classifier import safe_classifier
from backend.core.ai.dynamic_categories import dynamic_categories

router = APIRouter(prefix="/active-learning", tags=["Active Learning"])


# ============================================================
# Models
# ============================================================

class ClassifyRequest(BaseModel):
    """Request for document classification"""
    doc_id: int
    user_name: Optional[str] = "Boris"


class ClassifyResponse(BaseModel):
    """Classification response with Active Learning"""
    action: str  # "auto_classified" | "needs_confirmation"
    doc_id: int
    
    # For "auto_classified"
    category: Optional[str] = None
    confidence: Optional[float] = None
    
    # For "needs_confirmation" (Active Learning)
    frage: Optional[str] = None
    vorschlag: Optional[str] = None
    alternativen: Optional[List[str]] = None
    document_preview: Optional[str] = None


class UserExplanationRequest(BaseModel):
    """User's free-text explanation"""
    doc_id: int
    explanation: str  # FREE TEXT! No dropdowns!
    user_name: Optional[str] = "Boris"


class UserExplanationResponse(BaseModel):
    """Response after learning from user"""
    status: str  # "learned"
    category: str
    message: str
    document_filed: bool


class EscalationRequest(BaseModel):
    """User is also unsure → escalate to dev team"""
    doc_id: int
    user_comment: Optional[str] = None
    user_name: Optional[str] = "Boris"


class EscalationResponse(BaseModel):
    """Escalation confirmation"""
    status: str  # "escalated"
    message: str
    queue_position: int


# ============================================================
# Endpoints
# ============================================================

@router.post("/classify", response_model=ClassifyResponse)
async def classify_document(
    request: ClassifyRequest,
    db: Session = Depends(get_db)
):
    """
    Klassifiziert Dokument mit Active Learning.
    
    Flow:
    - Confidence >= 85% → auto_classified
    - Confidence < 85% → needs_confirmation (Active Learning Dialog)
    """
    # Get document
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.ocr_text:
        raise HTTPException(status_code=400, detail="Document has no OCR text")
    
    # Classify with Active Learning
    result = safe_classifier.classify_with_active_learning(
        text=doc.ocr_text,
        user_name=request.user_name
    )
    
    if result["status"] == "confident":
        # Auto-classify!
        category = result["class"]
        confidence = result["confidence"]
        
        # Update document
        doc.category = category
        doc.confidence = confidence
        doc.classification_status = "auto_classified"
        doc.classified_at = datetime.now()
        db.commit()
        
        logger.info(
            f"[ActiveLearning] ✓ Auto-classified doc {doc.id}: "
            f"{category} ({confidence:.2%})"
        )
        
        return ClassifyResponse(
            action="auto_classified",
            doc_id=doc.id,
            category=category,
            confidence=confidence
        )
    
    else:
        # Needs confirmation → Active Learning Dialog
        logger.info(
            f"[ActiveLearning] ⚠ Doc {doc.id} needs confirmation "
            f"(confidence: {result['confidence']:.2%})"
        )
        
        # Mark document as needing help
        doc.classification_status = "needs_user_help"
        doc.confidence = result["confidence"]
        db.commit()
        
        return ClassifyResponse(
            action="needs_confirmation",
            doc_id=doc.id,
            frage=result["frage"],
            vorschlag=result.get("vorschlag"),
            alternativen=result.get("alternativen", []),
            document_preview=f"/api/documents/{doc.id}/preview"
        )


@router.post("/explain", response_model=UserExplanationResponse)
async def user_explains_document(
    request: UserExplanationRequest,
    db: Session = Depends(get_db)
):
    """
    User erklärt Dokument mit FREIEM Text.
    
    Boris' Flow:
    1. User schreibt: "Das ist ein Wartungsvertrag für Röntgengeräte"
    2. VERA extrahiert: "Wartungsvertrag (Medizingeräte)"
    3. VERA lernt + bestätigt
    
    WICHTIG: KEINE vordefinierten Kategorien!
    User schreibt FREI → VERA extrahiert Kategorie!
    """
    # Get document
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get user (for attribution)
    # TODO: Get actual user from auth session
    user_id = 1  # Placeholder
    
    # Learn from user explanation
    learning_result = safe_classifier.learn_from_user_explanation(
        text=doc.ocr_text,
        user_explanation=request.explanation,
        user_id=user_id,
        user_name=request.user_name
    )
    
    category = learning_result["category"]
    
    # Update document with learned category
    doc.category = category
    doc.confidence = 1.0  # User-confirmed!
    doc.classification_status = "user_confirmed"
    doc.classified_at = datetime.now()
    doc.user_explanation = request.explanation
    db.commit()
    
    # Increment category usage
    dynamic_categories.increment_usage(category)
    
    logger.info(
        f"[ActiveLearning] ✓ User {request.user_name} explained doc {doc.id}: "
        f"'{category}'"
    )
    
    return UserExplanationResponse(
        status="learned",
        category=category,
        message=f"Danke! Ich habe gelernt: {category}",
        document_filed=True
    )


@router.post("/escalate", response_model=EscalationResponse)
async def escalate_to_dev_team(
    request: EscalationRequest,
    db: Session = Depends(get_db)
):
    """
    User ist auch unsicher → Escalation zu Developer Team.
    
    Boris' Requirement:
    "Wenn VERA gar nicht weiterkommt, muss VERA das Entwickler-Team fragen."
    """
    # Get document
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Mark for developer review
    doc.classification_status = "needs_dev_review"
    doc.user_comment = request.user_comment
    doc.escalated_at = datetime.now()
    doc.escalated_by = request.user_name
    db.commit()
    
    # Get queue position (how many docs waiting?)
    queue_count = db.query(Document).filter(
        Document.classification_status == "needs_dev_review"
    ).count()
    
    logger.warning(
        f"[ActiveLearning] ⚠ Doc {doc.id} escalated to dev team "
        f"by {request.user_name} (queue: {queue_count})"
    )
    
    return EscalationResponse(
        status="escalated",
        message="Okay, ich frage das Entwickler-Team. Dokument kommt in die Review-Queue.",
        queue_position=queue_count
    )


@router.get("/unclear-documents/count")
async def get_unclear_documents_count(
    db: Session = Depends(get_db)
):
    """
    Badge-Zähler für unklare Dokumente.
    
    Gibt nur die Anzahl wartender Dokumente zurück (für Badge im Menü).
    """
    # TEMPORARY FIX: Return 0 if classification_status column missing
    try:
        count = db.query(Document).filter(
            Document.classification_status.in_([
                "needs_user_help",
                "needs_dev_review",
                "processing"
            ])
        ).count()
    except Exception as e:
        logger.warning(f"Unable to count unclear documents (likely missing column): {e}")
        count = 0  # Fallback
    
    return {"count": count}


@router.get("/unclear-documents")
async def get_unclear_documents(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Liste aller unklaren Dokumente.
    
    Boris' Konzept:
    "So lange liegen diese Dokumente in einer Liste, 
     die noch nicht fertig bearbeitet ist."
    
    Status-Kategorien:
    - needs_user_help: User muss helfen (VERA unsicher)
    - needs_dev_review: Developer-Review nötig (User + VERA unsicher)
    - processing: OCR/Verarbeitung läuft noch
    """
    query = db.query(Document)
    
    if status_filter:
        query = query.filter(Document.classification_status == status_filter)
    else:
        # All unclear statuses
        query = query.filter(
            Document.classification_status.in_([
                "needs_user_help",
                "needs_dev_review",
                "processing"
            ])
        )
    
    docs = query.order_by(Document.created_at.desc()).all()
    
    # Group by status
    grouped = {
        "needs_user_help": [],
        "needs_dev_review": [],
        "processing": []
    }
    
    for doc in docs:
        status = doc.classification_status
        if status in grouped:
            grouped[status].append({
                "id": doc.id,
                "filename": doc.filename,
                "created_at": doc.created_at.isoformat(),
                "waiting_since": doc.created_at.isoformat(),
                "confidence": doc.confidence,
                "user_comment": doc.user_comment
            })
    
    return {
        "total": len(docs),
        "by_status": grouped,
        "counts": {
            "needs_user_help": len(grouped["needs_user_help"]),
            "needs_dev_review": len(grouped["needs_dev_review"]),
            "processing": len(grouped["processing"])
        }
    }


@router.get("/categories")
async def get_dynamic_categories(
    sort_by: str = "count"
):
    """
    Get all user-defined categories.
    
    Boris' Insight: "Kategorien sind UNBEGRENZT!"
    
    Returns:
        List of categories with usage stats
    """
    categories = dynamic_categories.get_all_categories(sort_by=sort_by)
    stats = dynamic_categories.get_stats()
    
    return {
        "categories": categories,
        "stats": stats
    }


@router.get("/stats")
async def get_active_learning_stats(
    db: Session = Depends(get_db)
):
    """
    Active Learning Statistics.
    
    Metrics:
    - Auto-classification rate
    - User help requests
    - Category growth
    - Escalation rate
    """
    # Document counts by status
    total_docs = db.query(Document).count()
    auto_classified = db.query(Document).filter(
        Document.classification_status == "auto_classified"
    ).count()
    user_confirmed = db.query(Document).filter(
        Document.classification_status == "user_confirmed"
    ).count()
    needs_help = db.query(Document).filter(
        Document.classification_status == "needs_user_help"
    ).count()
    needs_dev = db.query(Document).filter(
        Document.classification_status == "needs_dev_review"
    ).count()
    
    # Calculate rates
    auto_rate = (auto_classified / total_docs * 100) if total_docs > 0 else 0
    help_rate = ((needs_help + user_confirmed) / total_docs * 100) if total_docs > 0 else 0
    escalation_rate = (needs_dev / total_docs * 100) if total_docs > 0 else 0
    
    # Category stats
    category_stats = dynamic_categories.get_stats()
    
    return {
        "total_documents": total_docs,
        "auto_classified": auto_classified,
        "user_confirmed": user_confirmed,
        "needs_user_help": needs_help,
        "needs_dev_review": needs_dev,
        "auto_classification_rate": round(auto_rate, 1),
        "help_request_rate": round(help_rate, 1),
        "escalation_rate": round(escalation_rate, 1),
        "category_stats": category_stats
    }
