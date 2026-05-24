"""
VERA Office - Demo Classification API
Demo-Phase Workflow: Klassifiziere + User-Feedback sammeln

WORKFLOW:
1. System klassifiziert Dokument (mit Confidence)
2. User prüft und bestätigt ODER korrigiert
3. Feedback wird gespeichert (für Training)
4. Stats werden getrackt (für Monitoring)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.ai.safe_classifier import safe_classifier
from backend.core.ai.feedback_store import feedback_store

router = APIRouter(prefix="/demo", tags=["Demo Classification"])


# ============================================================
# Models
# ============================================================

class ClassificationResult(BaseModel):
    """Classification result for demo phase"""
    doc_id: int
    prediction: str
    confidence: float
    needs_review: bool
    suggestion: Optional[str] = None
    reasoning: str
    message: str


class FeedbackRequest(BaseModel):
    """User feedback on classification"""
    doc_id: int
    correct_class: str
    was_correct: bool  # True wenn Prediction korrekt war
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback response"""
    success: bool
    message: str


class DemoStatsResponse(BaseModel):
    """Demo phase statistics"""
    total_classified: int
    user_confirmations: int
    user_corrections: int
    accuracy: float
    avg_confidence: float
    low_confidence_count: int
    pending_review: int


# ============================================================
# Demo Classification Endpoints
# ============================================================

@router.post("/classify", response_model=ClassificationResult)
async def demo_classify(doc_id: int, db: Session = Depends(get_db)):
    """
    Klassifiziert Dokument mit 3-Stufen Confidence System (Boris' Update).
    
    3-STUFEN SYSTEM:
    1. ≥95%: Auto-Klassifikation (keine User-Action)
    2. 75-95%: Quick Confirm (1-Click Bestätigung)
    3. <75%: Volle Erklärung nötig
    
    Args:
        doc_id: Document ID
    
    Returns:
        Classification result mit action (auto_classified / confirm_with_suggestion / needs_explanation)
    """
    # Dokument laden
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        logger.warning(f"[DEMO] Document {doc_id} not found")
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    if not doc.ocr_text:
        logger.warning(f"[DEMO] Document {doc_id} has no OCR text")
        raise HTTPException(status_code=400, detail="Dokument hat keinen OCR-Text")
    
    # 3-Stufen Classification
    try:
        result = safe_classifier.classify_with_confidence_levels(doc.ocr_text)
        
        action = result["action"]
        confidence = result["confidence"]
        
        # STUFE 1: Auto-Klassifikation (≥95%)
        if action == "auto_classified":
            predicted_class = result["class"]
            
            # Log für Stats
            _log_demo_classification(
                doc_id=doc_id,
                prediction=predicted_class,
                confidence=confidence,
                needs_review=False
            )
            
            logger.info(f"[DEMO] Doc {doc_id}: AUTO {predicted_class} ({confidence:.2%})")
            
            return ClassificationResult(
                doc_id=doc_id,
                prediction=predicted_class,
                confidence=confidence,
                needs_review=False,
                suggestion=None,
                reasoning=result["reasoning"],
                message=f"✓ Automatisch klassifiziert als '{predicted_class}' ({confidence:.0%})"
            )
        
        # STUFE 2: Quick Confirm (75-95%)
        elif action == "confirm_with_suggestion":
            vorschlag = result["vorschlag"]
            frage = result["frage"]
            
            # Log für Stats
            _log_demo_classification(
                doc_id=doc_id,
                prediction=vorschlag,
                confidence=confidence,
                needs_review=True
            )
            
            logger.info(f"[DEMO] Doc {doc_id}: QUICK CONFIRM {vorschlag} ({confidence:.2%})")
            
            return ClassificationResult(
                doc_id=doc_id,
                prediction=vorschlag,
                confidence=confidence,
                needs_review=True,
                suggestion=vorschlag,
                reasoning=frage,
                message=f"⚠️ {frage}"
            )
        
        # STUFE 3: Volle Erklärung (<75%)
        else:  # needs_explanation
            frage = result["frage"]
            
            # Log für Stats
            _log_demo_classification(
                doc_id=doc_id,
                prediction="UNBEKANNT",
                confidence=confidence,
                needs_review=True
            )
            
            logger.warning(f"[DEMO] Doc {doc_id}: NEEDS EXPLANATION ({confidence:.2%})")
            
            return ClassificationResult(
                doc_id=doc_id,
                prediction="UNBEKANNT",
                confidence=confidence,
                needs_review=True,
                suggestion=None,
                reasoning=frage,
                message=f"❌ {frage}"
            )
    
    except Exception as e:
        logger.error(f"[DEMO] Classification failed for doc {doc_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Klassifikation fehlgeschlagen: {str(e)}")


@router.post("/confirm-suggestion", response_model=FeedbackResponse)
async def confirm_suggestion(doc_id: int, confirmed_class: str, db: Session = Depends(get_db)):
    """
    User bestätigt VERA's Vorschlag (Stufe 2: Quick Confirm).
    
    1-Click Bestätigung: User klickt "Ja, richtig" ohne weitere Eingabe.
    
    Args:
        doc_id: Document ID
        confirmed_class: Von VERA vorgeschlagene Kategorie
    
    Returns:
        Success response
    """
    # Dokument laden
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    # Kategorie finden
    category = db.query(Category).filter(Category.name == confirmed_class).first()
    if not category:
        logger.warning(f"[DEMO] Category '{confirmed_class}' not found")
        raise HTTPException(status_code=404, detail=f"Kategorie '{confirmed_class}' nicht gefunden")
    
    # Update Dokument
    doc.category_id = category.id
    doc.classification_confidence = 0.85  # Mid-range (Stufe 2)
    doc.classification_reasoning = f"User bestätigte VERA's Vorschlag (Quick Confirm)"
    
    db.commit()
    
    # Feedback speichern (CRITICAL für Training!)
    if doc.ocr_text:
        feedback_store.add_feedback(
            ocr_text=doc.ocr_text[:2000],
            category=confirmed_class,
            confirmed_by_user=True,
            auto_confirmed=False,
            confidence=0.85,
            was_suggestion=True  # Wichtig: Das war ein Vorschlag!
        )
        logger.info(f"[DEMO] ✓ Quick Confirm: Doc {doc_id} → {confirmed_class}")
    
    return FeedbackResponse(
        success=True,
        message=f"✓ Bestätigt: '{category.display_name}'"
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def demo_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    User gibt Feedback zu Klassifikation.
    
    Workflow:
    1. User bestätigt Prediction ODER korrigiert
    2. Feedback wird in feedback_store gespeichert (für Training!)
    3. Dokument wird aktualisiert
    4. Stats werden updated
    
    Args:
        request: Feedback mit correct_class und was_correct flag
    
    Returns:
        Success response
    """
    # Dokument laden
    doc = db.query(Document).filter(Document.id == request.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    # Kategorie finden
    category = db.query(Category).filter(Category.name == request.correct_class).first()
    if not category:
        logger.warning(f"[DEMO] Category '{request.correct_class}' not found")
        raise HTTPException(status_code=404, detail=f"Kategorie '{request.correct_class}' nicht gefunden")
    
    # Update Dokument
    old_category = doc.category.name if doc.category else "None"
    doc.category_id = category.id
    doc.classification_confidence = 1.0  # User = 100% confident
    
    if request.was_correct:
        doc.classification_reasoning = f"User bestätigt (Demo-Phase)"
    else:
        doc.classification_reasoning = f"User korrigiert: {old_category} → {request.correct_class} (Demo-Phase)"
    
    db.commit()
    
    # Feedback speichern (CRITICAL für Training!)
    if doc.ocr_text:
        feedback_store.add_feedback(
            ocr_text=doc.ocr_text[:2000],
            category=request.correct_class,
            confirmed_by_user=True,  # User Feedback = highest weight
            auto_confirmed=False,
            confidence=1.0
        )
        logger.info(f"[DEMO] ✓ Feedback stored: Doc {request.doc_id} → {request.correct_class}")
    
    # Stats updaten
    _update_demo_stats(
        doc_id=request.doc_id,
        was_correct=request.was_correct,
        correct_class=request.correct_class
    )
    
    # Response
    if request.was_correct:
        message = f"✓ Bestätigt: '{category.display_name}'"
        logger.success(f"[DEMO] Doc {request.doc_id} confirmed as {request.correct_class}")
    else:
        message = f"✓ Korrigiert auf '{category.display_name}'"
        logger.success(f"[DEMO] Doc {request.doc_id} corrected: {old_category} → {request.correct_class}")
    
    return FeedbackResponse(
        success=True,
        message=message
    )


@router.get("/stats", response_model=DemoStatsResponse)
async def get_demo_stats():
    """
    Demo-Phase Statistiken.
    
    Zeigt:
    - Wie viele Dokumente klassifiziert
    - Wie viele User-Bestätigungen
    - Wie viele Korrekturen
    - Accuracy (Bestätigungen / Gesamt)
    - Durchschnittliche Confidence
    - Wie viele Low-Confidence (Review nötig)
    
    Returns:
        Demo statistics
    """
    try:
        stats = _calculate_demo_stats()
        
        # Alert bei hoher Fehlerrate
        if stats["accuracy"] < 0.85 and stats["total_classified"] > 20:
            logger.warning(f"⚠️ DEMO: Accuracy nur {stats['accuracy']:.1%}! Review nötig!")
        
        return DemoStatsResponse(**stats)
    
    except Exception as e:
        logger.error(f"[DEMO] Stats calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Stats-Berechnung fehlgeschlagen")


# ============================================================
# Helper Functions
# ============================================================

def _log_demo_classification(doc_id: int, prediction: str, confidence: float, needs_review: bool):
    """
    Log classification für Demo-Stats.
    Speichert in separater Demo-Log-Tabelle.
    """
    # TODO: Implement demo_log table
    # For now: Just log to file
    logger.info(f"[DEMO-LOG] {doc_id} | {prediction} | {confidence:.2%} | Review: {needs_review}")


def _update_demo_stats(doc_id: int, was_correct: bool, correct_class: str):
    """
    Update Demo-Stats nach User-Feedback.
    """
    # TODO: Implement demo_stats table
    logger.info(f"[DEMO-STATS] {doc_id} | Correct: {was_correct} | Class: {correct_class}")


def _calculate_demo_stats() -> dict:
    """
    Calculate demo phase statistics from feedback_store.
    """
    total_feedback = feedback_store.get_total_feedback_count()
    
    # User confirmations (confirmed_by_user=True)
    # TODO: Query feedback_store for user-confirmed entries
    user_confirmations = 0
    user_corrections = 0
    
    # Simplified calculation (real implementation needs DB queries)
    total_classified = total_feedback
    accuracy = 0.85 if total_classified > 0 else 0.0  # Placeholder
    avg_confidence = 0.85  # Placeholder
    low_confidence_count = 0  # Placeholder
    pending_review = 0  # Placeholder
    
    return {
        "total_classified": total_classified,
        "user_confirmations": user_confirmations,
        "user_corrections": user_corrections,
        "accuracy": accuracy,
        "avg_confidence": avg_confidence,
        "low_confidence_count": low_confidence_count,
        "pending_review": pending_review
    }
