"""
User Model für VERA Office
Rollen-basiertes Benutzermodell: admin, editor, viewer, scanner
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.db.database import Base


# Definierte Rollen und ihre Berechtigungen
ROLES = {
    "admin": {
        "label": "Administrator",
        "permissions": ["read", "write", "delete", "upload", "scan", "export", "settings", "users", "modules"]
    },
    "editor": {
        "label": "Bearbeiter",
        "permissions": ["read", "write", "upload", "scan", "export"]
    },
    "viewer": {
        "label": "Betrachter",
        "permissions": ["read", "export"]
    },
    "scanner": {
        "label": "Scanner",
        "permissions": ["upload", "scan"]
    }
}


def role_has_permission(role: str, permission: str) -> bool:
    """Prüft ob eine Rolle eine bestimmte Berechtigung hat."""
    role_def = ROLES.get(role)
    if not role_def:
        return False
    return permission in role_def["permissions"]


class User(Base):
    """
    User-Tabelle mit Rollen-System.
    
    Rollen: admin, editor, viewer, scanner
    Migration: is_admin bleibt für Rückwärtskompatibilität,
    wird aber aus role abgeleitet.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    email = Column(String(255), nullable=True)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default="viewer", nullable=False)  # admin, editor, viewer, scanner
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Legacy, abgeleitet von role
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def has_permission(self, permission: str) -> bool:
        """Prüft ob User eine bestimmte Berechtigung hat."""
        return role_has_permission(self.role, permission)
    
    @property
    def permissions(self):
        """Gibt alle Berechtigungen des Users zurück."""
        role_def = ROLES.get(self.role, {})
        return role_def.get("permissions", [])
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}', active={self.is_active})>"
