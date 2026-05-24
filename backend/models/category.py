"""
VERA Office - Category Model
Dokumentkategorien (Rechnung, Vertrag, Personalakte etc.)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from backend.db.database import Base


class Category(Base):
    """
    Kategorie-Tabelle
    Definiert Dokumenttypen (Rechnung, Vertrag, Personalakte, Behördenschreiben etc.)
    """
    __tablename__ = "categories"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Kategorie-Informationen
    name = Column(String(128), nullable=False, unique=True, index=True)
    display_name = Column(String(256), nullable=False)  # Anzeigename (z.B. "Eingangsrechnungen")
    description = Column(Text, nullable=True)
    
    # Ablage-Pfad
    storage_path = Column(String(512), nullable=False)  # z.B. "Finanzen/Rechnungen/Eingang"
    
    # Klassifikations-Keywords (für regelbasierte Klassifikation)
    keywords = Column(Text, nullable=True)  # Komma-separierte Liste
    
    # Retention Policy (Aufbewahrungsfrist)
    retention_years = Column(Integer, nullable=True)  # NULL = unbegrenzt, z.B. 10 für Rechnungen
    
    # System-Kategorie (darf nicht gelöscht werden)
    is_system = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Beziehungen
    documents = relationship("Document", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', storage_path='{self.storage_path}')>"
