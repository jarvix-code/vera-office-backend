"""
VERA Office - Feedback API
Allows users to correct AI classifications for continuous learning.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.ai.feedback_store import feedback_store

router = APIRouter(prefix="/feedback", tags=["Feedback"])  # main.py adds /api prefix


# ============================================================
# User Feedback (Bug Reports, Feature Requests) → Telegram
# ============================================================

import asyncio
import os
from fastapi import File, UploadFile, Form
from datetime import datetime
from pathlib import Path

class FeedbackSubmitResponse(BaseModel):
    """Feedback submit response"""
    success: bool
    message: str
    ticket_id: Optional[int] = None


@router.post("/submit", response_model=FeedbackSubmitResponse)
async def submit_feedback(
    type: str = Form(...),  # "bug", "feature", "question", "other"
    message: str = Form(...),
    screenshot: Optional[UploadFile] = File(None)
):
    """
    User sendet Feedback/Bug-Report via VERA UI.
    Wird an Telegram Bot weitergeleitet.
    
    Args:
        type: Feedback-Typ (bug, feature, question, other)
        message: Feedback-Text
        screenshot: Optional Screenshot
    
    Returns:
        Success Response mit Ticket-ID
    """
    try:
        # Save screenshot if provided
        screenshot_path = None
        if screenshot:
            media_dir = Path(__file__).parent.parent.parent / "data" / "feedback_media"
            media_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = media_dir / f"{timestamp}_{screenshot.filename}"
            
            with open(screenshot_path, "wb") as f:
                content = await screenshot.read()
                f.write(content)
            
            logger.info(f"Screenshot saved: {screenshot_path}")
        
        # Send to Telegram + Developer-Server (parallel)
        ticket_id, _ = await asyncio.gather(
            _send_to_telegram(type, message, screenshot_path),
            _forward_to_developer_server(type, message, screenshot_path),
        )

        logger.info(f"📝 User Feedback submitted: {type} | Ticket #{ticket_id}")

        return FeedbackSubmitResponse(
            success=True,
            message="Feedback erfolgreich gesendet! Danke für deine Hilfe.",
            ticket_id=ticket_id
        )
    
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}", exc_info=True)
        return FeedbackSubmitResponse(
            success=False,
            message=f"Fehler beim Senden: {str(e)}"
        )


async def _send_to_telegram(feedback_type: str, message: str, screenshot_path: Optional[Path] = None) -> int:
    """
    Sendet Feedback an Telegram Bot.
    Chat-ID wird aus vera.yaml gelesen (auto-discovered beim ersten Bot-Kontakt).
    """
    try:
        import httpx
        import yaml
        from backend.config import config

        config_file = config.BASE_DIR / "config" / "vera.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)

        telegram_config = yaml_config.get("telegram", {})
        bot_token = telegram_config.get("bot_token")
        admin_chat_id = telegram_config.get("chat_id", "")

        if not bot_token:
            logger.warning("Telegram Bot Token nicht konfiguriert")
            return 0

        if not admin_chat_id:
            logger.warning("Telegram chat_id nicht konfiguriert — schreibe dem Bot zuerst eine Nachricht")
            return 0

        type_map = {
            "bug": ("🐛", "Bug"),
            "feature": ("💡", "Feature Request"),
            "question": ("❓", "Frage"),
            "other": ("💬", "Sonstiges")
        }
        emoji, category = type_map.get(feedback_type, ("💬", "Feedback"))

        telegram_message = (
            f"{emoji} **{category}** (via VERA UI)\n\n"
            f"{message}\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = await client.post(url, json={
                "chat_id": admin_chat_id,
                "text": telegram_message,
                "parse_mode": "Markdown"
            })

            if screenshot_path and screenshot_path.exists():
                with open(screenshot_path, "rb") as photo_file:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                        data={"chat_id": admin_chat_id},
                        files={"photo": photo_file}
                    )

        logger.success("✅ Feedback an Telegram gesendet")
        return 999

    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return 0


async def _forward_to_developer_server(feedback_type: str, message: str,
                                        screenshot_path: Optional[Path] = None) -> bool:
    """
    Leitet Feedback an den Developer-Server weiter (POST http://localhost:9000/api/feedback).
    """
    try:
        import httpx

        payload = {
            "type": feedback_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "source": "vera_ui"
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "http://localhost:9000/api/feedback",
                json=payload
            )
            logger.info(f"Developer-Server Response: {response.status_code}")
            return response.status_code < 400

    except Exception as e:
        logger.warning(f"Developer-Server nicht erreichbar: {e}")
        return False


# ============================================================
# Document Classification Feedback (existing)
# ============================================================

class CorrectionRequest(BaseModel):
    """User correction request"""
    document_id: int
    correct_category: str
    comment: Optional[str] = None


class CorrectionResponse(BaseModel):
    """Correction response"""
    success: bool
    message: str
    new_category: str


@router.post("/correct", response_model=CorrectionResponse)
async def correct_classification(
    request: CorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    User corrects AI classification.
    
    This is the CRITICAL feedback loop for AI training:
    - Updates document category
    - Stores feedback with confirmed_by_user=True (weight=2.0)
    - TF-IDF vectorizer learns from this correction
    
    Frontend calls this when user clicks "Kategorie korrigieren".
    """
    # Find document
    doc = db.query(Document).filter(Document.id == request.document_id).first()
    if not doc:
        logger.warning(f"Feedback: Document {request.document_id} not found")
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Find category
    category = db.query(Category).filter(Category.name == request.correct_category).first()
    if not category:
        logger.warning(f"Feedback: Category '{request.correct_category}' not found")
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Old category for logging
    old_category = doc.category.name if doc.category else "None"
    
    # Update document
    doc.category_id = category.id
    doc.classification_confidence = 1.0  # User correction = 100% confident
    doc.classification_reasoning = f"User correction: {request.comment or 'Manual override'}"
    db.commit()
    
    # Add to feedback store (CRITICAL for AI learning!)
    if doc.ocr_text:
        feedback_store.add_feedback(
            ocr_text=doc.ocr_text[:2000],  # First 2000 chars
            category=request.correct_category,
            confirmed_by_user=True,  # ← THIS is what makes AI learn!
            auto_confirmed=False,
            confidence=1.0
        )
        logger.info(f"📚 Feedback stored: {request.document_id} → {request.correct_category} (User correction, weight=2.0)")
    else:
        logger.warning(f"Feedback: No OCR text for document {request.document_id}, skipping feedback store")
    
    logger.success(f"✅ User correction: {doc.filename} | {old_category} → {request.correct_category}")
    
    return CorrectionResponse(
        success=True,
        message=f"Kategorie erfolgreich geändert auf '{category.display_name}'",
        new_category=request.correct_category
    )


@router.get("/stats")
async def get_feedback_stats():
    """
    Returns feedback statistics.
    
    Shows how many corrections were made (learning progress).
    """
    total = feedback_store.get_total_feedback_count()
    by_category = feedback_store.get_category_stats()
    
    return {
        "total_feedbacks": total,
        "categories": by_category
    }
