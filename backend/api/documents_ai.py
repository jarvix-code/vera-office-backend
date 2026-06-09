"""
VERA Office - Documents AI API
AI-powered endpoints: classification, feedback, reclassify
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.ai.classifier import classifier
from backend.core.ai.feedback_store import feedback_store
from backend.core.ai.template_knowledge import sync_categories_to_db
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
    
    # Get available categories — auto-seed from YAML templates if DB is empty
    categories = db.query(Category).all()
    if not categories:
        seeded = sync_categories_to_db(db)
        logger.info(f"Auto-seeded {seeded} categories from YAML templates")
        categories = db.query(Category).all()
    if not categories:
        raise HTTPException(status_code=400, detail="No categories configured")
    
    category_list = [
        {"name": cat.name, "description": cat.display_name}
        for cat in categories
    ]
    
    # Classify
    try:
        result = await asyncio.to_thread(classifier.classify, document.ocr_text, category_list)
        
        # Update document if confidence is high enough
        if classifier.should_auto_file(result['confidence']):
            category = db.query(Category).filter(Category.name == result['category']).first()
            if category:
                document.category_id = category.id
                document.classification_confidence = result['confidence']
                document.classification_reasoning = result['reasoning'][:500]
                document.classification_status = "auto_classified"
                db.commit()
                
                logger.info(f"Document {document_id} auto-classified as {result['category']}")
        else:
            # Low confidence: mark as needing user review
            if result['confidence'] > 0 and result.get('category') not in (None, 'unknown'):
                document.classification_status = "needs_user_help"
                db.commit()
        
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


# ─── Bug #719 Fix: invoice-check endpoint ─────────────────────────────────────
# Root cause: documents.invoice_validation was set only by the workflow engine
# (validate_invoice action), but the /invoice-check endpoint was missing entirely.
# This caused GET /documents/31 to show invoice_validation='incomplete' while
# the workflow engine might report compliant=true — or vice versa.
# Fix: This endpoint runs the validation AND writes the result back to
# documents.invoice_validation so both endpoints always agree.

class InvoiceCheckResponse(BaseModel):
    """Response for invoice validation check."""
    document_id: int
    compliant: bool
    missing: list
    validation_result: str  # 'valid' | 'incomplete'
    checks: dict


@router.get("/{document_id}/invoice-check", response_model=InvoiceCheckResponse)
async def check_invoice(document_id: int, db: Session = Depends(get_db)):
    """
    Bug #719 Fix: Invoice validation check endpoint.

    Runs §14 UStG field validation on the document's OCR text.
    Writes result back to documents.invoice_validation to keep
    GET /documents/{id} and GET /documents/{id}/invoice-check consistent.

    Returns:
      compliant: true if >= 3 of 4 required fields are present
      missing: list of field names that failed the check
      validation_result: 'valid' | 'incomplete'
    """
    import re as _re

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.deleted == False
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    if not document.ocr_text:
        # No OCR text: cannot validate, treat as incomplete
        document.invoice_validation = "incomplete"
        db.commit()
        return InvoiceCheckResponse(
            document_id=document_id,
            compliant=False,
            missing=["has_mwst", "has_amount", "has_date", "has_sender"],
            validation_result="incomplete",
            checks={}
        )

    text = document.ocr_text.lower()

    # §14 UStG field checks
    checks = {
        "has_mwst": bool(_re.search(r"mwst|mehrwertsteuer|umsatzsteuer", text)),
        "has_amount": bool(_re.search(r"\d+[,\.]\d+\s*(eur|euro|€)", text)),
        "has_date": bool(_re.search(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", text)),
        "has_sender": bool(_re.search(r"(gmbh|ag|kg|ohg|gbr|co\.|ug|e\.v\.|inc|ltd)", text)),
    }

    missing = [field for field, ok in checks.items() if not ok]
    passed = sum(checks.values())
    compliant = passed >= 3
    validation_result = "valid" if compliant else "incomplete"

    # Bug #719 Fix: Always sync result back to documents.invoice_validation
    # This ensures GET /documents/{id} and GET /documents/{id}/invoice-check agree.
    document.invoice_validation = validation_result
    db.commit()

    logger.info(
        f"[invoice-check] doc={document_id} result={validation_result} "
        f"passed={passed}/4 missing={missing}"
    )

    return InvoiceCheckResponse(
        document_id=document_id,
        compliant=compliant,
        missing=missing,
        validation_result=validation_result,
        checks=checks,
    )


# ─── Bug #1254 Fix: Retro-OCR Endpoint ──────────────────────────────────────
# Root cause: Documents uploaded via hotfolder/inbox-batch had ocr_text=NULL
# because process_new_document() in main.py only handles images, not PDFs.
# This endpoint retrospectively runs OCR on all docs with ocr_text IS NULL.

class RetroOcrResponse(BaseModel):
    """Retro-OCR batch result"""
    total_without_ocr: int
    processed: int
    succeeded: int
    failed: int
    skipped: int


@router.post("/retro-ocr", response_model=RetroOcrResponse)
async def retro_ocr_all(db: Session = Depends(get_db)):
    """
    Bug #1254 Fix: Retrospective OCR for documents with ocr_text IS NULL.
    Uses existing PDFProcessor (PyMuPDF text-layer) + OCREngine (PaddleOCR fallback).
    Safe to re-run: skips docs that already have ocr_text.
    """
    from pathlib import Path as _Path
    from backend.config import config as _config
    from backend.core.pdf_processor import PDFProcessor
    from backend.core.ocr_engine import OCREngine as _OCREngine

    docs_without_ocr = db.query(Document).filter(
        Document.deleted == False,
        (Document.ocr_text == None) | (Document.ocr_text == "")
    ).all()

    total = len(docs_without_ocr)
    succeeded = 0
    failed = 0
    skipped = 0

    pdf_proc = PDFProcessor()
    ocr_engine = _OCREngine()

    for doc in docs_without_ocr:
        if not doc.file_path:
            skipped += 1
            continue

        # Resolve absolute path (file_path may be relative to DATA_DIR)
        file_path_str = doc.file_path
        abs_path = _Path(file_path_str)
        if not abs_path.is_absolute():
            abs_path = _config.DATA_DIR / file_path_str

        if not abs_path.exists():
            logger.warning(f"[retro-ocr] File not found for doc {doc.id}: {abs_path}")
            skipped += 1
            continue

        suffix = abs_path.suffix.lower()
        if suffix not in (".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"):
            skipped += 1
            continue

        ocr_text = None

        try:
            if suffix == ".pdf":
                # Method 1: PyMuPDF native text extraction (fast, works on Windows)
                if pdf_proc.has_ocr_text(abs_path):
                    extracted = pdf_proc.extract_text(abs_path)
                    if extracted and len(extracted.strip()) > 20:
                        ocr_text = extracted
                        logger.info(f"[retro-ocr] doc {doc.id}: text-layer {len(ocr_text)} chars")

                # Method 2: PaddleOCR for scan-PDFs (no embedded text)
                if not ocr_text:
                    ocr_raw, temp_imgs = pdf_proc.ocr_pdf(abs_path)
                    for img in temp_imgs:
                        try:
                            img.unlink()
                        except Exception:
                            pass
                    if ocr_raw and len(ocr_raw.strip()) > 10:
                        ocr_text = ocr_raw
                        logger.info(f"[retro-ocr] doc {doc.id}: paddle-pdf-ocr {len(ocr_text)} chars")
            else:
                # Image: use PaddleOCR engine directly
                ocr_text = ocr_engine.extract_text(abs_path)
                if ocr_text:
                    logger.info(f"[retro-ocr] doc {doc.id}: paddle-ocr {len(ocr_text)} chars")
        except Exception as e:
            logger.warning(f"[retro-ocr] OCR failed for doc {doc.id}: {e}")

        if ocr_text and len(ocr_text.strip()) > 0:
            try:
                doc.ocr_text = ocr_text[:50000]
                db.commit()
                succeeded += 1
            except Exception as e:
                db.rollback()
                logger.error(f"[retro-ocr] DB write failed for doc {doc.id}: {e}")
                failed += 1
        else:
            failed += 1
            logger.warning(f"[retro-ocr] No text for doc {doc.id} ({abs_path.name})")

    logger.info(f"[retro-ocr] Done: {succeeded} ok, {failed} failed, {skipped} skipped / {total} total")
    return RetroOcrResponse(
        total_without_ocr=total,
        processed=succeeded + failed,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
    )
