"""
VERA Office - USB Import API
Scannt USB-Geräte und importiert alle Dokumente (PDF, JPG, PNG).
Platform-aware: Windows (Laufwerksbuchstaben) + Linux (mount points).
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import platform
import shutil
import string
import uuid

from backend.db.database import get_db, SessionLocal
from backend.config import config
from backend.core.image_processor import ImageProcessor
from backend.core.ocr_engine import OCREngine
from backend.core.pdf_generator import PDFGenerator
from backend.core.ai.classifier import classifier
from backend.core.ai.namer import namer
from backend.core.ai.filer import filer
from backend.core.ai.feedback_store import feedback_store
from backend.models.document import Document
from backend.models.category import Category
from loguru import logger

router = APIRouter()

#  Platform detection 
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# USB Mount-Point (Linux Standard)
USB_MOUNT_PATH = Path("/media/usb0")
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

# In-memory progress tracking (single-appliance, no need for Redis)
_import_jobs: dict = {}


class USBFolder(BaseModel):
    name: str
    path: str
    file_count: int
    size_mb: float


class USBScanResponse(BaseModel):
    mounted: bool
    path: str
    file_count: int
    files: List[str]
    folders: List[USBFolder]  # NEW: Folder structure


class USBImportResponse(BaseModel):
    job_id: str
    total_files: int
    message: str


class USBImportProgress(BaseModel):
    job_id: str
    status: str  # "scanning" | "importing" | "done" | "error"
    total: int
    done: int
    errors: int
    error_details: List[str]
    current_file: Optional[str] = None


class USBDetectionResponse(BaseModel):
    detected: bool
    mount_path: Optional[str] = None
    file_count: int = 0


@router.get("/import-usb/scan", response_model=USBScanResponse)
async def scan_usb():
    """Scannt USB-Mount-Point und listet importierbare Dateien + Folder-Struktur."""
    # Check multiple common mount points
    mount_path = _find_usb_mount()
    
    if not mount_path:
        return USBScanResponse(
            mounted=False, 
            path=str(USB_MOUNT_PATH), 
            file_count=0, 
            files=[],
            folders=[]
        )
    
    files = _find_importable_files(mount_path)
    folders = _scan_folders(mount_path)
    
    return USBScanResponse(
        mounted=True,
        path=str(mount_path),
        file_count=len(files),
        files=[f.name for f in files],
        folders=folders
    )


class USBImportRequest(BaseModel):
    folders: Optional[List[str]] = None  # NEW: Optional folder filter


@router.post("/import-usb", response_model=USBImportResponse)
async def start_usb_import(request: USBImportRequest, background_tasks: BackgroundTasks):
    """Startet Batch-Import aller Dateien vom USB-Stick (optional: nur aus bestimmten Ordnern)."""
    mount_path = _find_usb_mount()
    
    if not mount_path:
        raise HTTPException(status_code=404, detail="Kein USB-Stick gefunden. Bitte einstecken und erneut versuchen.")
    
    # Filter by folders if specified
    if request.folders:
        files = []
        for folder_name in request.folders:
            folder_path = mount_path / folder_name
            if folder_path.exists() and folder_path.is_dir():
                files.extend(_find_importable_files(folder_path))
        logger.info(f"USB-Import: {len(files)} Dateien aus {len(request.folders)} Ordnern")
    else:
        files = _find_importable_files(mount_path)
        logger.info(f"USB-Import: {len(files)} Dateien (alle Ordner)")
    
    if not files:
        raise HTTPException(status_code=404, detail="Keine importierbaren Dateien gefunden (PDF, JPG, PNG).")
    
    job_id = str(uuid.uuid4())[:8]
    _import_jobs[job_id] = {
        "status": "importing",
        "total": len(files),
        "done": 0,
        "errors": 0,
        "error_details": [],
        "current_file": None,
    }
    
    background_tasks.add_task(_run_import, job_id, files)
    
    return USBImportResponse(
        job_id=job_id,
        total_files=len(files),
        message=f"{len(files)} Dateien werden importiert..."
    )


@router.get("/import-usb/progress/{job_id}", response_model=USBImportProgress)
async def get_import_progress(job_id: str):
    """Gibt den aktuellen Import-Fortschritt zurück."""
    if job_id not in _import_jobs:
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    
    job = _import_jobs[job_id]
    return USBImportProgress(job_id=job_id, **job)


@router.get("/import-usb/detect", response_model=USBDetectionResponse)
async def detect_usb():
    """Prüft ob ein USB-Stick eingesteckt ist (OHNE File-Scan für Performance)."""
    mount_path = _find_usb_mount()
    if mount_path:
        # NUR Pfad zurückgeben, KEIN File-Count (wäre zu langsam bei großen Drives)
        return USBDetectionResponse(detected=True, mount_path=str(mount_path), file_count=0)
    return USBDetectionResponse(detected=False)


# --- Helper Functions ---

def _find_usb_mount() -> Optional[Path]:
    """
    Sucht nach USB-Speichergeräten.
    Windows: Prüft Wechseldatenträger (D:-Z:) via Win32 API oder Heuristik.
    Linux:   Sucht unter /media/, /mnt/usb, /media/usb0.
    """
    if IS_WINDOWS:
        return _find_usb_windows()
    return _find_usb_linux()


def _find_usb_windows() -> Optional[Path]:
    """
    Findet USB-Laufwerke unter Windows.
    Akzeptiert REMOVABLE (USB-Sticks) UND FIXED (externe HDDs/SSDs).
    Nur C: wird als System-Drive ausgeschlossen.
    """
    try:
        import ctypes
        # GetDriveType: 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED
        for letter in string.ascii_uppercase[3:]:  # D: onwards (skip A:, B:, C:)
            drive = f"{letter}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
            
            # Accept both REMOVABLE (2) and FIXED (3) drives, exclude C:
            if drive_type in [2, 3] and letter != 'C':
                p = Path(drive)
                try:
                    if p.exists() and any(p.iterdir()):
                        # Skip if it looks like a Windows system drive
                        if (p / "Windows").exists() or (p / "Program Files").exists():
                            continue
                        logger.info(f"USB-Detection: {letter}: gefunden (Type: {drive_type})")
                        return p
                except (PermissionError, OSError):
                    continue
    except Exception as e:
        logger.debug(f"Win32 Drive-Detection fehlgeschlagen: {e}")

    # Fallback: just check common removable letters
    for letter in "DEFGH":
        p = Path(f"{letter}:\\")
        try:
            if p.exists() and p.is_dir() and any(p.iterdir()):
                # Skip if it looks like a fixed drive (has Windows/Program Files)
                if (p / "Windows").exists() or (p / "Program Files").exists():
                    continue
                return p
        except (PermissionError, OSError):
            continue
    return None


def _find_usb_linux() -> Optional[Path]:
    """Findet USB-Sticks unter Linux (/media/, /mnt/usb)."""
    # Check explicit path first
    if USB_MOUNT_PATH.exists() and USB_MOUNT_PATH.is_dir() and any(USB_MOUNT_PATH.iterdir()):
        return USB_MOUNT_PATH

    # Check /media/ for any mounted USB devices
    media_path = Path("/media")
    if media_path.exists():
        for entry in media_path.iterdir():
            if entry.is_dir() and any(entry.iterdir()):
                return entry

    # Check /mnt/usb as fallback
    mnt_usb = Path("/mnt/usb")
    if mnt_usb.exists() and mnt_usb.is_dir() and any(mnt_usb.iterdir()):
        return mnt_usb

    return None


def _find_importable_files(mount_path: Path) -> List[Path]:
    """Findet importierbare Dateien (PDFs, JPGs, PNGs) NUR in Top-Level (nicht rekursiv)."""
    files = []
    for pattern in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
        files.extend(list(mount_path.glob(pattern)))  # glob statt rglob = nur Top-Level!
    files.sort(key=lambda f: f.name)
    return files


def _scan_folders(mount_path: Path) -> List[dict]:
    """
    Scannt USB-Stick und gibt Folder-Struktur zurück (nur Top-Level, nicht rekursiv).
    Zeigt nur Ordner die importierbare Dateien enthalten.
    """
    folders = []
    
    try:
        for entry in mount_path.iterdir():
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            
            # Count files in this folder (NUR direkte Kinder, kein rglob!)
            files = []
            for pattern in ["*.pdf", "*.jpg", "*.jpeg", "*.png"]:
                files.extend(list(entry.glob(pattern)))  # glob statt rglob!
            
            if len(files) == 0:
                continue
            
            # Calculate folder size
            try:
                size_bytes = sum(f.stat().st_size for f in files)
                size_mb = size_bytes / (1024 * 1024)
            except:
                size_mb = 0.0
            
            folders.append({
                "name": entry.name,
                "path": str(entry.relative_to(mount_path)),
                "file_count": len(files),
                "size_mb": round(size_mb, 2)
            })
        
        # Sort by name
        folders.sort(key=lambda f: f["name"])
        
    except Exception as e:
        logger.error(f"Folder-Scan fehlgeschlagen: {e}")
    
    return folders


async def _run_import(job_id: str, files: List[Path]):
    """Background-Task: Importiert alle Dateien über die VERA-Pipeline."""
    job = _import_jobs[job_id]
    inbox_dir = config.DATA_DIR / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    
    for i, file_path in enumerate(files):
        job["current_file"] = file_path.name
        try:
            # Copy to inbox -> Hotfolder-Scanner picks it up OR process inline
            dest = inbox_dir / f"usb_{job_id}_{i:04d}_{file_path.name}"
            await asyncio.to_thread(shutil.copy2, file_path, dest)
            logger.info(f" USB-Import [{i+1}/{len(files)}]: {file_path.name} -> inbox")
            job["done"] = i + 1
        except Exception as e:
            logger.error(f"[ERROR] USB-Import Fehler bei {file_path.name}: {e}")
            job["errors"] += 1
            job["error_details"].append(f"{file_path.name}: {str(e)}")
            job["done"] = i + 1
    
    job["status"] = "done"
    job["current_file"] = None
    logger.info(f"[OK] USB-Import {job_id} abgeschlossen: {job['done']}/{job['total']} ({job['errors']} Fehler)")
