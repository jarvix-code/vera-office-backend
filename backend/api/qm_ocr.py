"""
QM OCR API - VERA kann QM-Dokumente selbst mit OCR verarbeiten
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from backend.db.database import SessionLocal
from backend.models.qm import QMDocument
from backend.core.ocr_engine import OCREngine
from backend.core.vera_brain import vera_brain
from loguru import logger
import time

router = APIRouter()


class OCRRequest(BaseModel):
    document_id: Optional[int] = None  # Single doc
    process_all: bool = False  # All docs without OCR


class OCRStatus(BaseModel):
    total: int = 0
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    current: Optional[str] = None


# Global status
_ocr_status = OCRStatus()


def process_qm_document_ocr(doc_id: int, db: SessionLocal):
    """Process OCR for a single QM document."""
    ocr = OCREngine()
    
    doc = db.query(QMDocument).filter(QMDocument.id == doc_id).first()
    if not doc:
        logger.error(f"Document {doc_id} not found")
        return False
    
    _ocr_status.current = doc.title
    
    # Get file path from content or file_path field
    file_path_str = None
    
    if doc.file_path:
        file_path_str = doc.file_path
    elif doc.content and doc.content.startswith("KIQM-Datei:"):
        file_path_str = doc.content.split("\n")[0].replace("KIQM-Datei: ", "").strip()
    
    if not file_path_str:
        logger.warning(f"No file path for {doc.title}")
        _ocr_status.skipped += 1
        return False
    
    file_path = Path(file_path_str)
    
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        _ocr_status.skipped += 1
        return False
    
    if file_path.suffix.lower() != ".pdf":
        logger.warning(f"Not a PDF: {file_path}")
        _ocr_status.skipped += 1
        return False
    
    try:
        # Run OCR
        logger.info(f"OCR: {doc.title}")
        start = time.time()
        ocr_text = ocr.extract_text_from_pdf(file_path)
        duration = int((time.time() - start) * 1000)
        
        if ocr_text and len(ocr_text.strip()) > 10:
            # Update document
            doc.file_path = str(file_path)
            doc.ocr_text = ocr_text[:50000]  # Max 50K
            db.commit()
            
            # Index in VERA Brain
            vera_brain.index_document(
                doc_type="qm",
                doc_id=doc.id,
                title=doc.title,
                ocr_text=ocr_text
            )
            
            logger.success(f"[OK] OCR complete: {doc.title} ({duration}ms, {len(ocr_text)} chars)")
            _ocr_status.processed += 1
            return True
        else:
            logger.warning(f"No OCR text extracted: {doc.title}")
            _ocr_status.errors += 1
            return False
            
    except Exception as e:
        logger.error(f"OCR failed for {doc.title}: {e}")
        _ocr_status.errors += 1
        return False


def process_all_qm_documents():
    """Background task: Process all QM documents without OCR."""
    db = SessionLocal()
    
    try:
        # Get all QM docs without OCR
        docs = db.query(QMDocument).filter(
            (QMDocument.ocr_text.is_(None)) | (QMDocument.ocr_text == "")
        ).all()
        
        _ocr_status.total = len(docs)
        _ocr_status.processed = 0
        _ocr_status.skipped = 0
        _ocr_status.errors = 0
        
        logger.info(f"[DOC] Processing {len(docs)} QM documents...")
        
        for doc in docs:
            process_qm_document_ocr(doc.id, db)
        
        logger.success(f"[OK] OCR batch complete!")
        logger.info(f"  Processed: {_ocr_status.processed}")
        logger.info(f"  Skipped: {_ocr_status.skipped}")
        logger.info(f"  Errors: {_ocr_status.errors}")
        
    finally:
        db.close()
        _ocr_status.current = None


@router.post("/qm/ocr")
async def run_qm_ocr(request: OCRRequest, background_tasks: BackgroundTasks):
    """
    VERA triggert OCR für QM-Dokumente.
    
    Beispiele:
    
    # Single document
    POST /api/qm/ocr
    {
        "document_id": 123
    }
    
    # All documents
    POST /api/qm/ocr
    {
        "process_all": true
    }
    """
    
    if request.process_all:
        # Background task
        background_tasks.add_task(process_all_qm_documents)
        return {
            "status": "started",
            "message": "OCR batch processing started"
        }
    
    elif request.document_id:
        # Single document (synchronous)
        db = SessionLocal()
        try:
            success = process_qm_document_ocr(request.document_id, db)
            
            if success:
                return {
                    "status": "success",
                    "document_id": request.document_id
                }
            else:
                raise HTTPException(status_code=400, detail="OCR failed")
        finally:
            db.close()
    
    else:
        raise HTTPException(status_code=400, detail="Either document_id or process_all required")


@router.get("/qm/ocr/status")
async def get_ocr_status():
    """
    VERA fragt OCR-Status ab.
    
    GET /api/qm/ocr/status
    """
    return _ocr_status.dict()
