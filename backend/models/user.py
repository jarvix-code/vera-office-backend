"""
User Model für VERA Office
Rollen-basiertes Benutzermodell: admin, editor, viewer, scanner
"""
import json
from datetime import datetime

import bcrypt
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
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

    # Neues Auth-System: PIN + Master-PW
    name = Column(String(100), nullable=True)  # Anzeigename (z.B. "Boris")
    master_pw_hash = Column(String(255), nullable=True)  # bcrypt hash Master-PW (8-stellig)
    pin_hash = Column(String(255), nullable=True)  # bcrypt hash Arbeits-PIN (6-stellig)
    modules_unlocked = Column(Text, nullable=True, default='[]')  # JSON: ["erp", "qm"]

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

    @property
    def modules_list(self) -> list:
        """Gibt die freigeschalteten Module als Liste zurück."""
        if not self.modules_unlocked:
            return []
        try:
            return json.loads(self.modules_unlocked)
        except Exception:
            return []

    def set_module_pin(self, pin: str):
        """Setzt eine neue Modul-PIN (bcrypt-gehasht)."""
        self.pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

    def verify_module_pin(self, pin: str) -> bool:
        """Prüft ob die Modul-PIN korrekt ist."""
        if not self.pin_hash:
            return False
        return bcrypt.checkpw(pin.encode(), self.pin_hash.encode())

    def unlock_module(self, module: str):
        """Fügt ein Modul zur Freischaltungsliste hinzu (idempotent)."""
        modules = self.modules_list
        if module not in modules:
            modules.append(module)
            self.modules_unlocked = json.dumps(modules)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}', active={self.is_active})>"
