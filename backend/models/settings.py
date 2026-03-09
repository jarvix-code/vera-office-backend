"""
VERA Office - Settings Model
Systemeinstellungen aus Onboarding-Wizard
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from backend.db.database import Base


class Settings(Base):
    """
    Settings-Tabelle
    Key-Value Store für Systemeinstellungen (aus Onboarding-Wizard)
    """
    __tablename__ = "settings"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Key-Value
    key = Column(String(128), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)  # JSON-serialisiert falls komplexes Objekt
    value_type = Column(String(32), nullable=False, default="string")  # string, int, bool, json
    
    # Beschreibung
    description = Column(Text, nullable=True)
    
    # Kategorie (für Gruppierung in UI)
    category = Column(String(64), nullable=True, index=True)  # z.B. "onboarding", "network", "email"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"


class OnboardingState(Base):
    """
    Onboarding-Status
    Speichert Fortschritt des Ersteinrichtungs-Wizards
    """
    __tablename__ = "onboarding_state"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Status
    completed = Column(Boolean, default=False)
    current_step = Column(Integer, default=1)
    total_steps = Column(Integer, default=5)
    
    # Wizard-Daten (JSON)
    company_profile = Column(JSON, nullable=True)  # Unternehmenstyp, Branche, Mitarbeiterzahl
    document_types = Column(JSON, nullable=True)  # Ausgewählte Dokumentkategorien
    network_config = Column(JSON, nullable=True)  # Internet, E-Mail, Netzwerkordner
    onboarding_chat_data = Column(JSON, nullable=True)  # Conversational onboarding state
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<OnboardingState(completed={self.completed}, step={self.current_step}/{self.total_steps})>"
