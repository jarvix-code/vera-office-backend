"""
VERA Office - DMS API
Endpunkte für das Document Management System (DMS) Modul im Frontend.
Liefert /api/dms/files (GET) und /api/dms/files/{id} (PATCH).

Bug #1177: Frontend ruft /api/dms/files — Route fehlte komplett.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as _func
from pydantic import BaseModel
from typing import List, Optional

from backend.db.database import get_db
from backend.models.document import Document

router = APIRouter()


# ── Response / Request Models ──────────────────────────────────────────────────

class DmsFile(BaseModel):
    """DMS-Datei wie vom Frontend erwartet (ModuleView.tsx DMSView)."""
    id: str
    name: str
    size: str
    modified: str
    type: str
    location: str
    category: str
    owner: str

    class Config:
        from_attributes = True


class DmsFilesResponse(BaseModel):
    files: List[DmsFile]


class DmsFilePatch(BaseModel):
    """Felder die per PATCH aktualisiert werden dürfen."""
    location: Optional[str] = None
    category: Optional[str] = None
    owner: Optional[str] = None


# ── Hilfsfunktion ──────────────────────────────────────────────────────────────

def _format_size(size_bytes: int) -> str:
    """Gibt Dateigröße als lesbare Zeichenkette zurück."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _doc_to_dms_file(doc: Document) -> DmsFile:
    """Konvertiert ein Document-ORM-Objekt in ein DmsFile."""
    category_name = doc.category.display_name if doc.category else (doc.sender or "Unbekannt")
    modified = doc.updated_at.strftime("%d.%m.%Y") if doc.updated_at else (
        doc.created_at.strftime("%d.%m.%Y") if doc.created_at else ""
    )
    return DmsFile(
        id=str(doc.id),
        name=doc.original_filename or doc.filename,
        size=_format_size(doc.file_size),
        modified=modified,
        type=doc.category.display_name if doc.category else "Allgemein",
        location=doc.file_path or "",
        category=category_name,
        owner=doc.sender or "",
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/files", response_model=DmsFilesResponse, tags=["DMS"])
async def list_dms_files(db: Session = Depends(get_db)):
    """
    GET /api/dms/files
    Liefert alle (nicht gelöschten) Dokumente als DMS-File-Liste.
    Dedupliziert nach original_filename (höchste ID gewinnt) — gleiche Logik wie /api/documents/list.
    """
    dedup_subq = (
        db.query(_func.max(Document.id).label("max_id"))
        .filter(Document.deleted == False)
        .group_by(_func.coalesce(Document.original_filename, Document.filename))
        .subquery()
    )
    documents = (
        db.query(Document)
        .filter(Document.id.in_(dedup_subq))
        .order_by(Document.created_at.desc())
        .all()
    )
    return DmsFilesResponse(files=[_doc_to_dms_file(d) for d in documents])


@router.patch("/files/{file_id}", response_model=DmsFile, tags=["DMS"])
async def patch_dms_file(
    file_id: int,
    patch: DmsFilePatch,
    db: Session = Depends(get_db),
):
    """
    PATCH /api/dms/files/{file_id}
    Aktualisiert location, category (sender) oder owner (sender) eines Dokuments.
    """
    doc = db.query(Document).filter(Document.id == file_id, Document.deleted == False).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Dokument {file_id} nicht gefunden")

    if patch.location is not None:
        doc.file_path = patch.location
    if patch.owner is not None:
        doc.sender = patch.owner
    # category is stored as free-text sender when no category object exists;
    # if the document has a proper category relationship it stays unchanged here —
    # full re-classification is handled by /api/documents/{id}/classify.

    db.commit()
    db.refresh(doc)
    return _doc_to_dms_file(doc)
