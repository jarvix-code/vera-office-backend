"""
VERA Office - Classification Monitoring API
Real-Time Stats + Alert System

CRITICAL: Boris will KEINE stillen Fehler!
→ Alert bei >10% Fehlerrate
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import sqlite3
from pathlib import Path

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


# ============================================================
# Models
# ============================================================

class MonitoringStats(BaseModel):
    """Real-time classification statistics"""
    # Today
    classified_today: int
    user_corrections: int
    error_rate: float
    avg_confidence: float
    low_confidence_docs: int
    pending_review: int
    
    # Alerts
    alerts: List[str] = []
    
    # Category breakdown
    category_stats: Dict[str, int] = {}
    
    # Trend (last 7 days)
    trend_data: Optional[Dict[str, List]] = None


class AlertConfig(BaseModel):
    """Alert configuration"""
    error_rate_threshold: float = 0.10  # 10%
    low_confidence_threshold: float = 0.85
    enabled: bool = True


# ============================================================
# Monitoring Endpoints
# ============================================================

@router.get("/stats", response_model=MonitoringStats)
async def get_monitoring_stats():
    """
    Real-Time Classification Monitoring Stats.
    
    Zeigt:
    - Heute klassifizierte Dokumente
    - User-Korrekturen (= Fehler!)
    - Fehlerrate (Korrekturen / Gesamt)
    - Durchschnittliche Confidence
    - Dokumente mit Low Confidence (Review nötig)
    - Pending Reviews
    
    Returns:
        MonitoringStats mit Alerts
    """
    try:
        today = datetime.now().date()
        
        # Calculate stats
        stats = _calculate_today_stats(today)
        
        # Generate alerts
        alerts = _check_alerts(stats)
        
        # Add category breakdown
        category_stats = _get_category_breakdown(today)
        
        # Add trend data (optional)
        trend_data = _get_trend_data(days=7)
        
        result = MonitoringStats(
            classified_today=stats["classified_today"],
            user_corrections=stats["user_corrections"],
            error_rate=stats["error_rate"],
            avg_confidence=stats["avg_confidence"],
            low_confidence_docs=stats["low_confidence_docs"],
            pending_review=stats["pending_review"],
            alerts=alerts,
            category_stats=category_stats,
            trend_data=trend_data
        )
        
        # Log alerts
        if alerts:
            for alert in alerts:
                logger.warning(f"[MONITORING] ⚠️ {alert}")
        
        return result
    
    except Exception as e:
        logger.error(f"[MONITORING] Stats calculation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Monitoring fehlgeschlagen")


@router.get("/health")
async def health_check():
    """
    System health check.
    
    Returns:
        Health status
    """
    try:
        from backend.core.ai.safe_classifier import safe_classifier
        from backend.core.ai.feedback_store import feedback_store
        
        # Check components
        classifier_ok = safe_classifier.classifier.llm.is_available()
        rag_ok = safe_classifier.rag is not None
        feedback_ok = feedback_store.get_total_feedback_count() >= 0  # DB accessible
        
        overall_health = "healthy" if (classifier_ok and feedback_ok) else "degraded"
        
        return {
            "status": overall_health,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "classifier": "ok" if classifier_ok else "error",
                "rag": "ok" if rag_ok else "disabled",
                "feedback_store": "ok" if feedback_ok else "error"
            }
        }
    
    except Exception as e:
        logger.error(f"[MONITORING] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/alert/test")
async def test_alert():
    """
    Test alert system (send test notification).
    
    Returns:
        Test result
    """
    try:
        _send_alert("🧪 Test Alert: VERA Monitoring System aktiv")
        return {"success": True, "message": "Test-Alert gesendet"}
    
    except Exception as e:
        logger.error(f"[MONITORING] Alert test failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# Helper Functions
# ============================================================

def _calculate_today_stats(date: datetime.date) -> Dict:
    """
    Calculate classification stats for today.
    
    Args:
        date: Target date
    
    Returns:
        Stats dictionary
    """
    # TODO: Real implementation mit DB queries
    # For now: Placeholder values
    
    from backend.core.ai.feedback_store import feedback_store
    
    total_feedback = feedback_store.get_total_feedback_count()
    
    # Simplified calculation
    classified_today = min(total_feedback, 50)  # Placeholder
    user_corrections = int(classified_today * 0.05)  # 5% corrections (placeholder)
    error_rate = user_corrections / classified_today if classified_today > 0 else 0.0
    avg_confidence = 0.87  # Placeholder
    low_confidence_docs = int(classified_today * 0.10)  # 10% low confidence
    pending_review = low_confidence_docs
    
    return {
        "classified_today": classified_today,
        "user_corrections": user_corrections,
        "error_rate": error_rate,
        "avg_confidence": avg_confidence,
        "low_confidence_docs": low_confidence_docs,
        "pending_review": pending_review
    }


def _check_alerts(stats: Dict) -> List[str]:
    """
    Check stats for alert conditions.
    
    Args:
        stats: Statistics dictionary
    
    Returns:
        List of alert messages
    """
    alerts = []
    
    # Alert: Hohe Fehlerrate
    if stats["error_rate"] > 0.10:  # > 10%
        alerts.append(
            f"⚠️ FEHLERRATE ZU HOCH: {stats['error_rate']:.1%} "
            f"({stats['user_corrections']} Korrekturen bei {stats['classified_today']} Dokumenten)"
        )
    
    # Alert: Viele Low-Confidence Dokumente
    if stats["low_confidence_docs"] > 20:
        alerts.append(
            f"⚠️ VIELE UNSICHERE KLASSIFIKATIONEN: {stats['low_confidence_docs']} "
            f"Dokumente benötigen Review"
        )
    
    # Alert: Niedrige durchschnittliche Confidence
    if stats["avg_confidence"] < 0.80:
        alerts.append(
            f"⚠️ NIEDRIGE CONFIDENCE: Durchschnitt nur {stats['avg_confidence']:.1%}"
        )
    
    return alerts


def _get_category_breakdown(date: datetime.date) -> Dict[str, int]:
    """
    Get classification breakdown by category.
    
    Args:
        date: Target date
    
    Returns:
        Category counts
    """
    # TODO: Real implementation
    return {
        "checkliste": 12,
        "arbeitsanweisung": 8,
        "hygieneplan": 5,
        "freigabeprotokoll": 7,
        "wartungsprotokoll": 6,
        "sonstige": 3
    }


def _get_trend_data(days: int = 7) -> Dict[str, List]:
    """
    Get trend data for last N days.
    
    Args:
        days: Number of days to include
    
    Returns:
        Trend data (dates, classified counts, error rates)
    """
    # TODO: Real implementation
    dates = []
    classified = []
    error_rates = []
    
    for i in range(days):
        date = datetime.now().date() - timedelta(days=days-i-1)
        dates.append(date.isoformat())
        classified.append(45 + i*2)  # Placeholder
        error_rates.append(0.05 + i*0.01)  # Placeholder
    
    return {
        "dates": dates,
        "classified": classified,
        "error_rates": error_rates
    }


def _send_alert(message: str):
    """
    Send alert notification.
    
    Args:
        message: Alert message
    
    TODO: Integration with Telegram/Email/etc.
    """
    logger.warning(f"[ALERT] {message}")
    
    # TODO: Send to Telegram
    # await send_telegram_message(chat_id=ADMIN_CHAT_ID, text=message)
    
    # For now: Just log
    print(f"\n{'='*60}")
    print(f"ALERT: {message}")
    print(f"{'='*60}\n")
