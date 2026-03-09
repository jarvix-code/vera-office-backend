"""
VERA Suggestion Engine
Proactive suggestions based on document analysis
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import func

from backend.db.database import SessionLocal
from backend.models.document import Document
from backend.models.category import Category

logger = logging.getLogger(__name__)


class Suggestion:
    """Represents a proactive suggestion."""
    
    def __init__(
        self,
        title: str,
        description: str,
        priority: str,  # "low", "medium", "high"
        action: str,  # "view", "classify", "archive", etc.
        action_data: dict = None
    ):
        self.title = title
        self.description = description
        self.priority = priority
        self.action = action
        self.action_data = action_data or {}
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "action": self.action,
            "action_data": self.action_data
        }


class SuggestionEngine:
    """Generates proactive suggestions based on system state."""
    
    def get_chat_suggestions(self, last_action: str = None) -> List[str]:
        """
        Get contextual chat suggestions based on last action and time of day.
        
        Args:
            last_action: Last action type (upload, search, classify, correct, etc.)
        
        Returns:
            List of suggestion strings for the chat UI
        """
        from datetime import datetime
        hour = datetime.now().hour
        
        if last_action == "upload":
            return ["Klassifizieren", "Umbenennen", "Ordner zuweisen"]
        elif last_action == "search":
            return ["Erneut suchen", "Filter erweitern", "Export"]
        elif last_action == "classify":
            return ["Nächstes Dokument", "Kategorie ändern", "Statistik"]
        elif last_action == "correct":
            return ["Nächstes Dokument", "Alle prüfen", "Statistik"]
        elif last_action == "delete":
            return ["Rückgängig?", "Nächstes Dokument", "Übersicht"]
        
        # Time-based defaults
        if hour < 9:
            pending = self._count_uncategorized()
            if pending > 0:
                return [f"{pending} neue Dokumente", "Was fehlt?", "Übersicht"]
            return ["Guten Morgen! ☀️", "Übersicht", "Was gibt's Neues?"]
        elif hour >= 17:
            return ["Alles erledigt?", "Offene Dokumente", "Schönen Feierabend! 👋"]
        
        return ["Dokument suchen", "Was fehlt?", "Übersicht"]
    
    def _count_uncategorized(self) -> int:
        """Count uncategorized documents."""
        db = SessionLocal()
        try:
            return db.query(Document).filter(Document.category_id.is_(None)).count()
        finally:
            db.close()
    
    def get_suggestions(self) -> List[Dict]:
        """
        Get all proactive suggestions.
        Checks for:
        - Uncategorized documents
        - Missing documents (patterns)
        - Expiring retention periods
        - Duplicate suspects
        
        Returns:
            List of suggestion dictionaries
        """
        suggestions = []
        
        # 1. Check for uncategorized documents
        uncategorized = self._check_uncategorized()
        if uncategorized:
            suggestions.append(uncategorized)
        
        # 2. Check for missing documents (patterns)
        missing = self._check_missing_patterns()
        suggestions.extend(missing)
        
        # 3. Check for expiring retention periods
        expiring = self._check_expiring_retention()
        suggestions.extend(expiring)
        
        # 4. Check for duplicate suspects
        duplicates = self._check_duplicates()
        if duplicates:
            suggestions.append(duplicates)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))
        
        return [s.to_dict() for s in suggestions]
    
    def _check_uncategorized(self) -> Suggestion:
        """Check for uncategorized documents."""
        db = SessionLocal()
        try:
            count = db.query(Document).filter(
                Document.category_id.is_(None)
            ).count()
            
            if count > 0:
                return Suggestion(
                    title=f"{count} unkategorisierte Dokumente",
                    description=f"Es gibt {count} Dokument(e), die noch keiner Kategorie zugeordnet sind.",
                    priority="medium" if count > 5 else "low",
                    action="view_uncategorized",
                    action_data={"count": count}
                )
        finally:
            db.close()
        
        return None
    
    def _check_missing_patterns(self) -> List[Suggestion]:
        """
        Check for missing documents based on patterns.
        Example: Monthly payslips, invoices, etc.
        """
        suggestions = []
        db = SessionLocal()
        
        try:
            # Check for monthly patterns (e.g., Gehaltsabrechnung)
            monthly_categories = db.query(Category).filter(
                Category.name.in_(["gehaltsabrechnung", "rechnung"])
            ).all()
            
            for category in monthly_categories:
                # Check last 3 months
                for i in range(1, 4):
                    month_ago = datetime.now() - timedelta(days=30 * i)
                    month_start = month_ago.replace(day=1, hour=0, minute=0, second=0)
                    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
                    
                    count = db.query(Document).filter(
                        Document.category_id == category.id,
                        Document.created_at >= month_start,
                        Document.created_at <= month_end
                    ).count()
                    
                    if count == 0 and i <= 2:  # Only suggest for last 2 months
                        suggestions.append(Suggestion(
                            title=f"Fehlende {category.display_name}",
                            description=f"Für {month_ago.strftime('%B %Y')} wurde noch keine {category.display_name} gefunden.",
                            priority="high" if i == 1 else "medium",
                            action="check_missing",
                            action_data={
                                "category": category.name,
                                "month": month_ago.strftime("%Y-%m")
                            }
                        ))
        
        except Exception as e:
            logger.error(f"Error checking missing patterns: {e}")
        
        finally:
            db.close()
        
        return suggestions
    
    def _check_expiring_retention(self) -> List[Suggestion]:
        """Check for documents approaching retention period expiry."""
        suggestions = []
        db = SessionLocal()
        
        try:
            # Get categories with retention periods
            categories = db.query(Category).filter(
                Category.retention_years.isnot(None)
            ).all()
            
            for category in categories:
                # Check documents older than (retention - 1 year)
                expiry_date = datetime.now() - timedelta(days=365 * (category.retention_years - 1))
                
                count = db.query(Document).filter(
                    Document.category_id == category.id,
                    Document.created_at <= expiry_date
                ).count()
                
                if count > 0:
                    suggestions.append(Suggestion(
                        title=f"Aufbewahrungsfrist läuft ab",
                        description=f"{count} Dokument(e) in '{category.display_name}' nähern sich dem Ende der Aufbewahrungsfrist ({category.retention_years} Jahre).",
                        priority="low",
                        action="view_expiring",
                        action_data={
                            "category": category.name,
                            "count": count
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error checking retention: {e}")
        
        finally:
            db.close()
        
        return suggestions
    
    def _check_duplicates(self) -> Suggestion:
        """Check for potential duplicate documents."""
        db = SessionLocal()
        
        try:
            # Find documents with same filename (excluding generated names)
            duplicates = db.query(
                Document.original_filename,
                func.count(Document.id).label('count')
            ).filter(
                Document.original_filename.isnot(None)
            ).group_by(
                Document.original_filename
            ).having(
                func.count(Document.id) > 1
            ).all()
            
            if duplicates:
                total_duplicates = sum([d.count - 1 for d in duplicates])
                
                return Suggestion(
                    title=f"Mögliche Duplikate",
                    description=f"Es wurden {len(duplicates)} Dateinamen gefunden, die mehrfach vorkommen ({total_duplicates} potentielle Duplikate).",
                    priority="low",
                    action="view_duplicates",
                    action_data={"count": len(duplicates)}
                )
        
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
        
        finally:
            db.close()
        
        return None


# Global instance
suggestion_engine = SuggestionEngine()
