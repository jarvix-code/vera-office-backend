"""
VERA Office - Workflow API
Manual trigger for document processing pipeline.
Bug #258 Fix: POST /api/workflow/run endpoint
Bug #725 Fix: already_synced false positive — physical path check before skip
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.ai.classifier import classifier
from backend.core.ai.namer import namer
from backend.core.ai.filer import filer
from backend.config import config
from loguru import logger

router = APIRouter()


class WorkflowRunRequest(BaseModel):
    """Request body for manual workflow trigger"""
    document_id: int
    force: bool = False  # Force re-run even if already classified


class WorkflowRunResponse(BaseModel):
    """Result of workflow run"""
    document_id: int
    status: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    filename: Optional[str] = None
    message: str


def _is_in_category_folder(file_path_str: str, category_name: str) -> bool:
    """
    Bug #725: Check whether the file physically resides inside the expected
    category folder (or any subfolder thereof).

    Returns True only when the file exists AND its path is under
    filer.get_category_path(category_name).
    """
    try:
        current_path = config.DATA_DIR / file_path_str
        if not current_path.exists():
            return False
        expected_category_root = filer.get_category_path(category_name)
        # Resolve both paths to handle symlinks / relative segments
        return str(current_path.resolve()).startswith(str(expected_category_root.resolve()))
    except Exception:
        return False


@router.post("/workflow/run", response_model=WorkflowRunResponse, tags=["Workflow"])
async def run_workflow(
    request: WorkflowRunRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger the processing pipeline for an existing document.

    Runs classification (+ optional naming/filing) for a document that
    is already in the database with OCR text available.

    Useful for documents that missed the automatic pipeline or need re-processing.
    """
    # Load document
    document = db.query(Document).filter(
        Document.id == request.document_id,
        Document.deleted == False
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")

    if not document.ocr_text:
        raise HTTPException(status_code=400, detail="No OCR text available — cannot run pipeline")

    # Bug #725 Fix: Skip only when BOTH conditions are met:
    #   1. DB flag says already classified (auto_classified)
    #   2. Physical file is actually in the correct category subfolder
    # If the file is still in the documents root, force re-filing regardless of DB flag.
    if document.classification_status == "auto_classified" and not request.force:
        category_name_for_check = document.category.name if document.category else None
        already_in_category = (
            category_name_for_check is not None
            and _is_in_category_folder(document.file_path, category_name_for_check)
        )
        if already_in_category:
            return WorkflowRunResponse(
                document_id=document.id,
                status="skipped",
                category=category_name_for_check,
                confidence=document.classification_confidence,
                message="Already classified and filed. Use force=true to re-run."
            )
        else:
            # DB says classified but file is not in category folder — refile it
            logger.warning(
                f"[Workflow] Bug #725: Doc {document.id} marked auto_classified "
                f"but file not in category folder '{category_name_for_check}'. Forcing refile."
            )

    # Load available categories
    categories = db.query(Category).all()
    if not categories:
        raise HTTPException(status_code=400, detail="No categories configured")

    category_list = [
        {"name": cat.name, "description": cat.display_name}
        for cat in categories
    ]

    # Step 1: Classification
    try:
        result = classifier.classify(document.ocr_text, category_list)
        category_name = result.get("category")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "")

        logger.info(f"[Workflow] Doc {document.id}: classified as {category_name} ({confidence:.2f})")
    except Exception as e:
        logger.error(f"[Workflow] Classification failed for doc {document.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {e}")

    # Update DB with classification result
    category_obj = db.query(Category).filter(Category.name == category_name).first()
    if category_obj:
        document.category_id = category_obj.id
        document.classification_confidence = confidence
        document.classification_reasoning = (reasoning or "")[:500]
        document.classification_status = "auto_classified"

    new_filename = document.filename

    # Step 2: Semantic naming (only if confidence high enough)
    if category_name and classifier.should_auto_file(confidence):
        try:
            semantic_filename = namer.generate_filename(
                document.ocr_text,
                category_name,
                original_filename=document.filename
            )
            if semantic_filename and semantic_filename != document.filename:
                # Rename file on disk
                current_path = config.DATA_DIR / document.file_path
                if current_path.exists():
                    new_path = current_path.parent / semantic_filename
                    current_path.rename(new_path)
                    document.filename = semantic_filename
                    document.file_path = str(new_path.relative_to(config.DATA_DIR))
                    new_filename = semantic_filename
                    logger.info(f"[Workflow] Doc {document.id}: renamed to {semantic_filename}")
        except Exception as e:
            logger.warning(f"[Workflow] Naming failed for doc {document.id}: {e}")

        # Step 3: Auto-filing into category folder
        # Bug #725: Always update file_path in DB after successful move
        try:
            current_path = config.DATA_DIR / document.file_path
            if current_path.exists():
                filed_path = filer.file_document(
                    source_path=str(current_path),
                    category=category_name
                )
                document.file_path = str(Path(filed_path).relative_to(config.DATA_DIR))
                new_filename = Path(filed_path).name
                logger.info(f"[Workflow] Doc {document.id}: filed to {filed_path}")
        except Exception as e:
            logger.warning(f"[Workflow] Filing failed for doc {document.id}: {e}")

    try:
        db.commit()
        db.refresh(document)
    except Exception as e:
        db.rollback()
        logger.error(f"[Workflow] DB commit failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return WorkflowRunResponse(
        document_id=document.id,
        status="completed",
        category=category_name,
        confidence=confidence,
        reasoning=reasoning[:200] if reasoning else None,
        filename=new_filename,
        message=f"Pipeline completed for document {document.id}"
    )
