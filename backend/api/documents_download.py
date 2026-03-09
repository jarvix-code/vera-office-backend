"""
VERA Office - Document Download Endpoint
Missing endpoint that was referenced in frontend but never implemented.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from backend.db.database import get_db
from backend.models.document import Document
from backend.config import config
from loguru import logger

router = APIRouter()


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Download document PDF.
    
    Frontend calls: documentsApi.download(id)
    Returns: PDF file as attachment
    """
    # Find document in DB
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        logger.warning(f"Download failed: Document {document_id} not found in DB")
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Build file path
    file_path = config.DATA_DIR / doc.file_path
    if not file_path.exists():
        logger.error(f"Download failed: File not found on disk: {file_path}")
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    logger.info(f"📥 Download: {doc.filename} (ID: {document_id})")
    
    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"'
        }
    )
