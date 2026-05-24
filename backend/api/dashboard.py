"""
VERA Office - Dashboard API
Provides aggregated data for the main dashboard
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from loguru import logger

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class CriticalAlert(BaseModel):
    """Critical alert that requires immediate action"""
    id: int
    title: str
    description: str
    icon: str
    route: str


class Warning(BaseModel):
    """Warning for upcoming deadlines"""
    id: int
    title: str
    description: str
    icon: str
    route: str


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    new_documents: int
    unclassified: int
    storage_used: float  # GB
    storage_total: float  # GB
    storage_percent: float
    total_documents: int


class RecentActivity(BaseModel):
    """Recent document activity"""
    id: int
    title: str
    description: str
    icon: str
    color: str
    time: str


class DashboardData(BaseModel):
    """Complete dashboard data"""
    critical_alerts: List[CriticalAlert]
    warnings: List[Warning]
    stats: DashboardStats
    recent_activities: List[RecentActivity]


@router.get("", response_model=DashboardData)
async def get_dashboard_data(db: Session = Depends(get_db)):
    """
    Get all dashboard data in one call.
    
    Returns:
        - Critical alerts (red): Immediate action required
        - Warnings (yellow): Upcoming deadlines
        - Stats: Document counts, storage, etc.
        - Recent activities: Timeline of latest changes
    """
    try:
        # Time ranges
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        
        # --- STATS ---
        total_docs = db.query(Document).filter(Document.deleted == False).count()
        
        new_docs = db.query(Document).filter(
            and_(
                Document.created_at >= last_7_days,
                Document.deleted == False
            )
        ).count()
        
        unclassified = db.query(Document).filter(
            and_(
                Document.category_id == None,
                Document.deleted == False
            )
        ).count()
        
        # Storage calculation (sum of file_size in bytes -> GB)
        total_size_bytes = db.query(func.sum(Document.file_size)).filter(
            Document.deleted == False
        ).scalar() or 0
        storage_used = round(total_size_bytes / (1024**3), 2)  # Convert to GB
        
        # Assume 512 GB total storage (TODO: Get from system)
        storage_total = 512.0
        storage_percent = round((storage_used / storage_total) * 100, 1)
        
        stats = DashboardStats(
            new_documents=new_docs,
            unclassified=unclassified,
            storage_used=storage_used,
            storage_total=storage_total,
            storage_percent=storage_percent,
            total_documents=total_docs
        )
        
        # --- CRITICAL ALERTS ---
        critical_alerts = []
        
        # Unclassified documents older than 7 days
        old_unclassified = db.query(Document).filter(
            and_(
                Document.category_id == None,
                Document.created_at < last_7_days,
                Document.deleted == False
            )
        ).count()
        
        if old_unclassified > 0:
            critical_alerts.append(CriticalAlert(
                id=1,
                title=f"{old_unclassified} unklassifizierte Dokumente",
                description="Älter als 7 Tage - bitte kategorisieren",
                icon="help_outline",
                route="/documents?filter=unclassified"
            ))
        
        # Storage warning (>80%)
        if storage_percent > 80:
            critical_alerts.append(CriticalAlert(
                id=2,
                title="Speicherplatz knapp",
                description=f"{storage_percent}% belegt - bitte Dokumente archivieren",
                icon="storage",
                route="/settings"
            ))
        
        # --- WARNINGS ---
        warnings = []
        
        # New unclassified documents (< 7 days)
        if unclassified > old_unclassified:
            warnings.append(Warning(
                id=1,
                title=f"{unclassified - old_unclassified} neue Dokumente",
                description="Warten auf Klassifizierung",
                icon="schedule",
                route="/documents?filter=unclassified"
            ))
        
        # --- RECENT ACTIVITIES ---
        recent_docs = db.query(Document).filter(
            Document.deleted == False
        ).order_by(Document.created_at.desc()).limit(10).all()
        
        recent_activities = []
        for idx, doc in enumerate(recent_docs):
            time_diff = now - doc.created_at
            if time_diff.total_seconds() < 3600:  # < 1 hour
                time_str = f"vor {int(time_diff.total_seconds() / 60)} Min"
            elif time_diff.total_seconds() < 86400:  # < 1 day
                time_str = f"vor {int(time_diff.total_seconds() / 3600)} Std"
            else:
                time_str = f"vor {time_diff.days} Tagen"
            
            recent_activities.append(RecentActivity(
                id=idx + 1,
                title=doc.filename or "Unbenannt",
                description=f"Hochgeladen und {doc.category.display_name if doc.category else 'nicht klassifiziert'}",
                icon="upload_file",
                color="teal" if doc.category else "amber",
                time=time_str
            ))
        
        return DashboardData(
            critical_alerts=critical_alerts,
            warnings=warnings,
            stats=stats,
            recent_activities=recent_activities
        )
    
    except Exception as e:
        logger.error(f"Dashboard data error: {e}", exc_info=True)
        # Return empty dashboard on error
        return DashboardData(
            critical_alerts=[],
            warnings=[],
            stats=DashboardStats(
                new_documents=0,
                unclassified=0,
                storage_used=0.0,
                storage_total=512.0,
                storage_percent=0.0,
                total_documents=0
            ),
            recent_activities=[]
        )
