"""
OCR API endpoints for KI-Erfassung module
Provides /api/ocr/jobs (GET) and /api/ocr/upload (POST)
"""
import uuid
import asyncio
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from backend.config import config

router = APIRouter(prefix="/api/ocr", tags=["OCR"])

# In-memory job store (keyed by job_id)
_jobs: Dict[str, dict] = {}


class OcrJobStatus(BaseModel):
    job_id: str
    filename: str
    status: str          # "queued" | "processing" | "done" | "error"
    progress: Optional[int] = None   # 0-100
    result: Optional[str] = None     # extracted text summary
    error: Optional[str] = None


@router.get("/jobs")
async def list_ocr_jobs():
    """
    Return all OCR jobs (active and recently completed).
    Frontend expects: { jobs: OcrJobStatus[] }
    """
    jobs = list(_jobs.values())
    return {"jobs": jobs}


async def _run_ocr(job_id: str, file_path: Path):
    """Background task: run OCR on the uploaded file and update job status."""
    _jobs[job_id]["status"] = "processing"
    _jobs[job_id]["progress"] = 10

    try:
        from backend.core.ocr_engine import OCREngine
        from backend.core.image_processor import ImageProcessor

        ocr = OCREngine()
        suffix = file_path.suffix.lower()

        _jobs[job_id]["progress"] = 30

        if suffix == ".pdf":
            from backend.core.pdf_processor import PDFProcessor
            pdf_proc = PDFProcessor()
            text, _tmp_images = await asyncio.to_thread(pdf_proc.ocr_pdf, file_path)
            # Clean up any temp images produced
            for img in _tmp_images:
                Path(img).unlink(missing_ok=True)
        else:
            # Image file: preprocess then extract text
            processor = ImageProcessor()
            processed = file_path.parent / f"processed_{file_path.stem}.jpg"
            await asyncio.to_thread(processor.process, file_path, processed)
            text = await asyncio.to_thread(ocr.extract_text, processed)
            processed.unlink(missing_ok=True)

        _jobs[job_id]["progress"] = 90

        if text and len(text.strip()) > 0:
            # Store a short preview (first 200 chars) as result
            _jobs[job_id]["result"] = text.strip()[:200]
            _jobs[job_id]["status"] = "done"
            logger.success(f"OCR job {job_id} completed ({len(text)} chars)")
        else:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["result"] = "(Kein Text erkannt)"
            logger.warning(f"OCR job {job_id}: no text extracted")

        _jobs[job_id]["progress"] = 100

    except Exception as e:
        logger.error(f"OCR job {job_id} failed: {e}")
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)
    finally:
        # Clean up uploaded file
        file_path.unlink(missing_ok=True)


@router.post("/upload")
async def upload_for_ocr(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accept a file upload and queue it for OCR processing.
    Supported: PDF, PNG, JPG, JPEG, TIFF, BMP
    Returns: { message, job_id }
    """
    allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Nicht unterstütztes Dateiformat: {suffix}. Erlaubt: {', '.join(allowed_suffixes)}"
        )

    # Save uploaded file to inbox
    job_id = str(uuid.uuid4())
    inbox_dir = config.INBOX_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    dest = inbox_dir / f"ocr_{job_id}{suffix}"

    content = await file.read()
    dest.write_bytes(content)
    logger.info(f"OCR upload: {file.filename} → {dest} (job {job_id})")

    # Register job
    _jobs[job_id] = {
        "job_id": job_id,
        "filename": file.filename or dest.name,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }

    # Process in background
    background_tasks.add_task(_run_ocr, job_id, dest)

    return {
        "message": f'Datei "{file.filename}" zur Verarbeitung übermittelt',
        "job_id": job_id,
    }
