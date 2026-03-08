"""
VERA Office - System API
Status, Health, Updates
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import psutil
import platform
from pathlib import Path

from backend.config import config
from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.services.update_client import get_update_client
from backend.core.ai.brain import brain

router = APIRouter()


# Response Models
class SystemStatus(BaseModel):
    """System-Status Response"""
    app_name: str
    version: str
    uptime: float  # Sekunden
    status: str
    debug_mode: bool


class SystemStats(BaseModel):
    """System-Statistiken"""
    total_documents: int
    total_categories: int
    storage_used_mb: float
    storage_available_mb: float
    cpu_percent: float
    memory_percent: float
    last_document_date: datetime | None


class HealthResponse(BaseModel):
    """Health Check Response"""
    status: str
    timestamp: datetime
    database: str
    hotfolder: str
    storage: str


# Startup-Zeitpunkt (für Uptime)
_startup_time = datetime.utcnow()


@router.get("/status", response_model=SystemStatus)
async def get_status():
    """
    Gibt aktuellen System-Status zurück
    """
    uptime = (datetime.utcnow() - _startup_time).total_seconds()
    
    return SystemStatus(
        app_name=config.APP_NAME,
        version=config.APP_VERSION,
        uptime=uptime,
        status="running",
        debug_mode=config.DEBUG
    )


@router.get("/stats", response_model=SystemStats)
async def get_stats(db: Session = Depends(get_db)):
    """
    Gibt System-Statistiken zurück
    """
    # Dokument-Statistiken
    total_documents = db.query(func.count(Document.id)).filter(Document.deleted == False).scalar() or 0
    total_categories = db.query(func.count(Category.id)).scalar() or 0
    
    # Letztes Dokument
    last_doc = db.query(Document.created_at).filter(Document.deleted == False).order_by(Document.created_at.desc()).first()
    last_document_date = last_doc[0] if last_doc else None
    
    # Storage
    documents_path = config.DOCUMENTS_DIR
    if documents_path.exists():
        storage_used = sum(f.stat().st_size for f in documents_path.rglob('*') if f.is_file())
        storage_used_mb = storage_used / (1024 * 1024)
    else:
        storage_used_mb = 0.0
    
    # Verfügbarer Speicher
    disk = psutil.disk_usage(str(config.DATA_DIR))
    storage_available_mb = disk.free / (1024 * 1024)
    
    # System-Ressourcen
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory_percent = psutil.virtual_memory().percent
    
    return SystemStats(
        total_documents=total_documents,
        total_categories=total_categories,
        storage_used_mb=round(storage_used_mb, 2),
        storage_available_mb=round(storage_available_mb, 2),
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        last_document_date=last_document_date
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Detaillierter Health Check
    Prüft: Datenbank, Hotfolder, Storage
    """
    # Datenbank-Check
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Hotfolder-Check
    hotfolder_status = "ok" if config.INBOX_DIR.exists() else "missing"
    
    # Storage-Check
    disk = psutil.disk_usage(str(config.DATA_DIR))
    storage_status = "ok" if disk.free > 1024 * 1024 * 100 else "low"  # Warnung bei < 100MB
    
    overall_status = "healthy" if all([
        db_status == "ok",
        hotfolder_status == "ok",
        storage_status == "ok"
    ]) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database=db_status,
        hotfolder=hotfolder_status,
        storage=storage_status
    )


@router.get("/info")
async def system_info():
    """
    System-Informationen (Hardware, OS, Pfade)
    """
    return {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation()
        },
        "hardware": {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_total_gb": round(psutil.disk_usage(str(config.DATA_DIR)).total / (1024**3), 2)
        },
        "paths": {
            "data_dir": str(config.DATA_DIR),
            "inbox": str(config.INBOX_DIR),
            "documents": str(config.DOCUMENTS_DIR),
            "database": str(config.DATABASE_URL)
        },
        "config": {
            "debug": config.DEBUG,
            "hotfolder_enabled": config.HOTFOLDER_ENABLED,
            "ocr_language": config.OCR_LANGUAGE,
            "classification_threshold": config.CLASSIFICATION_THRESHOLD
        }
    }


# ============================================================
# Update-System Endpoints
# ============================================================

class UpdateStatusResponse(BaseModel):
    """Update-Status Response"""
    current_version: str
    update_available: bool
    latest_version: Optional[str]
    auto_update_enabled: bool
    last_check: Optional[datetime]


class UpdateCheckResponse(BaseModel):
    """Update-Check Response"""
    update_available: bool
    version: Optional[str]
    changelog: Optional[str]
    download_url: Optional[str]


@router.get("/update-status", response_model=UpdateStatusResponse)
async def get_update_status():
    """
    Gibt aktuellen Update-Status zurueck.
    
    Returns:
        Update-Status (Version, verfuegbare Updates, Auto-Update)
    """
    update_client = get_update_client()
    
    if not update_client:
        return UpdateStatusResponse(
            current_version=config.APP_VERSION,
            update_available=False,
            latest_version=None,
            auto_update_enabled=False,
            last_check=None
        )
    
    return UpdateStatusResponse(
        current_version=update_client.current_version,
        update_available=False,  # TODO: Cache last check result
        latest_version=None,
        auto_update_enabled=update_client.auto_update,
        last_check=update_client._last_check
    )


@router.post("/check-update", response_model=UpdateCheckResponse)
async def check_for_updates():
    """
    Prueft manuell auf Updates.
    
    Returns:
        Update-Info falls verfuegbar
    """
    update_client = get_update_client()
    
    if not update_client:
        return UpdateCheckResponse(
            update_available=False,
            version=None,
            changelog=None,
            download_url=None
        )
    
    update_info = await update_client.check_for_updates()
    
    if update_info:
        return UpdateCheckResponse(
            update_available=True,
            version=update_info.get("version"),
            changelog=update_info.get("changelog"),
            download_url=update_info.get("download_url")
        )
    
    return UpdateCheckResponse(
        update_available=False,
        version=None,
        changelog=None,
        download_url=None
    )


class ApplyUpdateRequest(BaseModel):
    """Update-Apply Request"""
    version: str


class ApplyUpdateResponse(BaseModel):
    """Update-Apply Response"""
    success: bool
    message: str
    version: Optional[str] = None


@router.post("/apply-update", response_model=ApplyUpdateResponse)
async def apply_update(request: ApplyUpdateRequest):
    """
    Lädt ein Update herunter, verifiziert es und wendet es an.
    
    Args:
        request: Version die installiert werden soll
    
    Returns:
        Erfolg/Fehler mit Nachricht
    """
    update_client = get_update_client()
    
    if not update_client:
        return ApplyUpdateResponse(
            success=False,
            message="Update-Client nicht konfiguriert"
        )
    
    try:
        # 1. Download
        zip_path = await update_client.download_update(request.version)
        if not zip_path:
            return ApplyUpdateResponse(
                success=False,
                message=f"Download von Version {request.version} fehlgeschlagen"
            )
        
        # 2. Hash verifizieren (wenn verfügbar)
        if hasattr(update_client, 'verify_sha256'):
            if not update_client.verify_sha256(zip_path):
                return ApplyUpdateResponse(
                    success=False,
                    message="SHA256-Hash stimmt nicht überein — Update abgelehnt"
                )
        
        # 3. Anwenden
        success = await update_client.apply_update(zip_path)
        if success:
            return ApplyUpdateResponse(
                success=True,
                message=f"✅ Update auf Version {request.version} erfolgreich installiert.\n⚠️ Neustart erforderlich!",
                version=request.version
            )
        else:
            return ApplyUpdateResponse(
                success=False,
                message="Update konnte nicht angewendet werden — siehe Server-Logs"
            )
    except Exception as e:
        logger.error(f"Update-Fehler: {e}", exc_info=True)
        return ApplyUpdateResponse(
            success=False,
            message=f"Fehler: {str(e)}"
        )


@router.get("/brain-stats")
async def get_brain_stats():
    """VERAs Lernstand — wie schlau ist sie?"""
    return brain.get_stats()


@router.post("/brain-seed")
async def seed_brain():
    """Initialisiert Basis-Domänenwissen (einmalig beim ersten Start)."""
    brain.seed_domain_knowledge()
    return {"status": "ok", "message": "Domänenwissen geladen"}


@router.get("/version")
async def get_version():
    """Gibt aktuelle VERA-Version zurueck."""
    return {
        "version": config.APP_VERSION,
        "app_name": config.APP_NAME
    }
