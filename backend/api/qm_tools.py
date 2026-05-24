"""
VERA Office - QM Tools API
Tools for VERA to manage QM documents (find duplicates, delete, etc.)
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from pydantic import BaseModel
from typing import List

from backend.db.database import SessionLocal
from backend.models.qm import QMDocument
from loguru import logger

router = APIRouter()


class DuplicateReport(BaseModel):
    total_documents: int
    duplicate_groups: int
    duplicates_found: int
    duplicates_deleted: int
    kept_documents: int


class DuplicateGroup(BaseModel):
    title: str
    count: int
    ids: List[int]


@router.post("/qm/remove-duplicates", response_model=DuplicateReport)
async def remove_qm_duplicates():
    """
    Findet und löscht Duplikate in QM-Dokumenten.
    Kriterium: Gleicher Titel + main_area.
    Behält jeweils das ÄLTESTE Dokument (created_at).
    """
    db = SessionLocal()
    
    try:
        # Count total before
        total_before = db.query(QMDocument).count()
        
        # Find duplicate groups (same title + main_area)
        duplicates_query = (
            db.query(
                QMDocument.title,
                QMDocument.main_area,
                func.count(QMDocument.id).label('count')
            )
            .group_by(QMDocument.title, QMDocument.main_area)
            .having(func.count(QMDocument.id) > 1)
        )
        
        duplicate_groups = duplicates_query.all()
        
        deleted_count = 0
        
        for title, main_area, count in duplicate_groups:
            # Get all docs in this group, ordered by created_at (oldest first)
            docs = (
                db.query(QMDocument)
                .filter(QMDocument.title == title, QMDocument.main_area == main_area)
                .order_by(QMDocument.created_at.asc())
                .all()
            )
            
            # Keep first (oldest), delete rest
            for doc in docs[1:]:
                # Delete directly without cascade (avoid revision table issues)
                db.query(QMDocument).filter(QMDocument.id == doc.id).delete()
                deleted_count += 1
                logger.info(f"Deleted duplicate: {doc.title} (ID {doc.id})")
        
        db.commit()
        
        total_after = db.query(QMDocument).count()
        
        logger.success(f"[OK] Removed {deleted_count} QM duplicates ({len(duplicate_groups)} groups)")
        
        return DuplicateReport(
            total_documents=total_before,
            duplicate_groups=len(duplicate_groups),
            duplicates_found=sum(count - 1 for _, _, count in duplicate_groups),
            duplicates_deleted=deleted_count,
            kept_documents=total_after
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] Duplicate removal failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        db.close()


@router.get("/qm/find-duplicates")
async def find_qm_duplicates():
    """
    Findet Duplikate OHNE zu löschen (Preview).
    """
    db = SessionLocal()
    
    try:
        duplicates_query = (
            db.query(
                QMDocument.title,
                QMDocument.main_area,
                func.count(QMDocument.id).label('count')
            )
            .group_by(QMDocument.title, QMDocument.main_area)
            .having(func.count(QMDocument.id) > 1)
        )
        
        duplicate_groups = []
        
        for title, main_area, count in duplicates_query.all():
            docs = (
                db.query(QMDocument.id)
                .filter(QMDocument.title == title, QMDocument.main_area == main_area)
                .all()
            )
            
            duplicate_groups.append({
                "title": title,
                "main_area": main_area,
                "count": count,
                "ids": [doc.id for doc in docs]
            })
        
        total_duplicates = sum(group["count"] - 1 for group in duplicate_groups)
        
        return {
            "duplicate_groups": len(duplicate_groups),
            "total_duplicates": total_duplicates,
            "groups": duplicate_groups[:10]  # Show first 10
        }
        
    finally:
        db.close()
