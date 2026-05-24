"""
VERA Office - KIQM Import
Import legacy KIQM documents into VERA QM module.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import sqlite3
import uuid
from loguru import logger

from backend.db.database import SessionLocal
from backend.modules.qm.models import QMDocument

router = APIRouter()

# KIQM Database path
KIQM_DB_PATH = Path("C:/Jarvix/QM/data/qmki.db")

# Area mapping
AREA_MAP = {
    "as": "Arbeitssicherheit",
    "qm": "Qualitätsmanagement", 
    "hb": "Handbuch"
}

# In-memory progress tracking
_import_jobs: dict = {}


class KIQMScanResponse(BaseModel):
    available: bool
    path: str
    document_count: int
    by_area: dict


class KIQMImportResponse(BaseModel):
    job_id: str
    total_documents: int
    message: str


class KIQMImportProgress(BaseModel):
    job_id: str
    status: str  # "scanning" | "importing" | "done" | "error"
    total: int
    done: int
    errors: int
    error_details: List[str]
    current_document: Optional[str] = None


@router.get("/import-kiqm/scan", response_model=KIQMScanResponse)
async def scan_kiqm():
    """Scannt KIQM-Datenbank und listet verfügbare Dokumente."""
    
    if not KIQM_DB_PATH.exists():
        return KIQMScanResponse(
            available=False,
            path=str(KIQM_DB_PATH),
            document_count=0,
            by_area={}
        )
    
    try:
        conn = sqlite3.connect(KIQM_DB_PATH)
        cur = conn.cursor()
        
        # Count total
        total = cur.execute("SELECT COUNT(*) FROM document_templates").fetchone()[0]
        
        # Count by area
        by_area = {}
        for row in cur.execute("SELECT area, COUNT(*) FROM document_templates GROUP BY area"):
            area_code, count = row
            area_name = AREA_MAP.get(area_code, area_code)
            by_area[area_name] = count
        
        conn.close()
        
        return KIQMScanResponse(
            available=True,
            path=str(KIQM_DB_PATH),
            document_count=total,
            by_area=by_area
        )
        
    except Exception as e:
        logger.error(f"KIQM scan failed: {e}")
        return KIQMScanResponse(
            available=False,
            path=str(KIQM_DB_PATH),
            document_count=0,
            by_area={}
        )


@router.post("/import-kiqm", response_model=KIQMImportResponse)
async def start_kiqm_import(background_tasks: BackgroundTasks):
    """Startet Batch-Import aller KIQM-Dokumente."""
    
    if not KIQM_DB_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"KIQM-Datenbank nicht gefunden: {KIQM_DB_PATH}"
        )
    
    # Count documents
    conn = sqlite3.connect(KIQM_DB_PATH)
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM document_templates").fetchone()[0]
    conn.close()
    
    if total == 0:
        raise HTTPException(status_code=404, detail="Keine Dokumente zum Importieren gefunden.")
    
    job_id = str(uuid.uuid4())[:8]
    _import_jobs[job_id] = {
        "status": "importing",
        "total": total,
        "done": 0,
        "errors": 0,
        "error_details": [],
        "current_document": None,
    }
    
    background_tasks.add_task(_run_import, job_id)
    
    return KIQMImportResponse(
        job_id=job_id,
        total_documents=total,
        message=f"{total} KIQM-Dokumente werden importiert..."
    )


@router.get("/import-kiqm/progress/{job_id}", response_model=KIQMImportProgress)
async def get_import_progress(job_id: str):
    """Gibt den aktuellen Import-Fortschritt zurück."""
    if job_id not in _import_jobs:
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    
    job = _import_jobs[job_id]
    return KIQMImportProgress(job_id=job_id, **job)


# --- Background Task ---

def _run_import(job_id: str):
    """
    Background-Task: Importiert alle KIQM documents.
    """
    job = _import_jobs[job_id]
    
    try:
        # Connect to databases
        kiqm_conn = sqlite3.connect(KIQM_DB_PATH)
        kiqm_cur = kiqm_conn.cursor()
        
        # Fetch all templates
        kiqm_cur.execute("""
            SELECT id, title, area, chapter, file_path, file_type, version, meta_data
            FROM document_templates
        """)
        
        templates = kiqm_cur.fetchall()
        job["total"] = len(templates)
        
        # Use SQLAlchemy session for VERA DB
        db = SessionLocal()
        
        for idx, row in enumerate(templates):
            doc_id, title, area, chapter, file_path, file_type, version, meta_data = row
            
            job["current_document"] = title
            
            try:
                # Map area to VERA format
                main_area = AREA_MAP.get(area, "Handbuch")
                
                # Extract chapter ID (e.g., "01_BeitrO..." -> "hb_01")
                blzk_chapter_id = None
                if chapter:
                    parts = chapter.split("_")
                    if len(parts) >= 1:
                        blzk_chapter_id = f"{area}_{parts[0]}"
                
                # Create QM document
                doc = QMDocument(
                    title=title,
                    main_area=main_area,
                    content=f"Importiert aus KIQM: {file_path or 'N/A'}",
                    status="Freigegeben",  # Assume all KIQM docs are approved
                    current_version=version or "1.0",
                    created_at=datetime.now()
                )
                
                db.add(doc)
                db.commit()
                
                job["done"] += 1
                
                if job["done"] % 100 == 0:
                    logger.info(f"KIQM import progress: {job['done']}/{job['total']}")
                
            except Exception as e:
                job["errors"] += 1
                error_msg = f"{title}: {str(e)}"
                job["error_details"].append(error_msg)
                logger.warning(f"KIQM import error: {error_msg}")
                db.rollback()
        
        db.close()
        kiqm_conn.close()
        
        job["status"] = "done"
        job["current_document"] = None
        
        logger.success(f"[OK] KIQM import complete: {job['done']}/{job['total']} (errors: {job['errors']})")
        
    except Exception as e:
        job["status"] = "error"
        job["error_details"].append(f"Fatal error: {str(e)}")
        logger.error(f"[ERROR] KIQM import failed: {e}")
