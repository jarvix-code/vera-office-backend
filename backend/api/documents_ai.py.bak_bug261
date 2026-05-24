"""
VERA Office - Documents AI API
AI-powered endpoints: classification, feedback, reclassify
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.ai.classifier import classifier
from backend.core.ai.feedback_store import feedback_store
from loguru import logger

router = APIRouter()


class ClassificationResponse(BaseModel):
    """Classification result"""
    category: str
    confidence: float
    reasoning: str
    available: bool


class FeedbackRequest(BaseModel):
    """User feedback on classification"""
    correct_category: str  # User-corrected or confirmed category
    was_correct: bool  # True if AI was correct, False if user corrected


class ReclassifyRequest(BaseModel):
    """Manual reclassification request"""
    force: bool = False  # Force reclassification even if already classified


@router.post("/{document_id}/classify", response_model=ClassificationResponse)
async def classify_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually classify a document using AI.
    Useful for documents uploaded before AI was enabled.
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.ocr_text:
        raise HTTPException(status_code=400, detail="No OCR text available for classification")
    
    # Get available categories
    categories = db.query(Category).all()
    if not categories:
        raise HTTPException(status_code=400, detail="No categories configured")
    
    category_list = [
        {"name": cat.name, "description": cat.display_name}
        for cat in categories
    ]
    
    # Classify
    try:
        result = classifier.classify(document.ocr_text, category_list)
        
        # Update document if confidence is high enough
        if classifier.should_auto_file(result['confidence']):
            category = db.query(Category).filter(Category.name == result['category']).first()
            if category:
                document.category_id = category.id
                document.classification_confidence = result['confidence']
                document.classification_reasoning = result['reasoning'][:500]
                db.commit()
                
                logger.info(f"Document {document_id} auto-classified as {result['category']}")
        
        return ClassificationResponse(
            category=result['category'],
            confidence=result['confidence'],
            reasoning=result['reasoning'],
            available=result['available']
        )
    
    except Exception as e:
        logger.error(f"Classification failed for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/feedback")
async def submit_feedback(
    document_id: int,
    feedback: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit user feedback on document classification.
    This helps the AI learn from corrections.
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.ocr_text:
        raise HTTPException(status_code=400, detail="No OCR text available")
    
    # Validate category exists
    category = db.query(Category).filter(Category.name == feedback.correct_category).first()
    if not category:
        raise HTTPException(status_code=400, detail=f"Category not found: {feedback.correct_category}")
    
    # Update document category
    document.category_id = category.id
    
    # Higher confidence if user confirmed (was already correct)
    if feedback.was_correct:
        document.classification_confidence = 1.0
    
    db.commit()
    
    # Add to feedback store for learning
    try:
        feedback_store.add_feedback(
            ocr_text=document.ocr_text[:2000],
            category=feedback.correct_category,
            confirmed_by_user=True,
            confidence=document.classification_confidence
        )
        
        logger.info(f"Feedback added for document {document_id}: {feedback.correct_category} (correct={feedback.was_correct})")
    
    except Exception as e:
        logger.error(f"Failed to add feedback: {e}")
    
    return {
        "status": "ok",
        "message": "Feedback submitted successfully",
        "category": feedback.correct_category,
        "total_feedback": feedback_store.get_total_feedback_count()
    }


@router.get("/feedback/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """
    Get feedback statistics (learning progress).
    """
    stats = feedback_store.get_category_stats()
    total = feedback_store.get_total_feedback_count()
    
    return {
        "total_feedback": total,
        "by_category": stats,
        "ready_for_learning": total >= 10  # Arbitrary threshold
    }
