"""
VERA Office - Document Model
Repräsentiert ein verarbeitetes Dokument in der Datenbank
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.db.database import Base


class Document(Base):
    """
    Dokument-Tabelle
    Speichert Metadaten über verarbeitete Dokumente
    """
    __tablename__ = "documents"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Dateiinformationen
    filename = Column(String(512), nullable=False, index=True)
    original_filename = Column(String(512), nullable=True)
    file_path = Column(String(1024), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)  # Bytes
    file_hash = Column(String(64), nullable=True, index=True)  # SHA256 für Duplikaterkennung
    
    # Dokumenttyp & Klassifikation
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", back_populates="documents")
    classification_confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    
    # OCR & Inhalt
    ocr_text = Column(Text, nullable=True)  # Volltext aus OCR
    ocr_language = Column(String(10), nullable=True, default="de")
    ocr_corrected = Column(Boolean, default=False)  # Wurde KI-Korrektur angewendet?
    
    # Intelligente Metadaten (aus Klassifikation extrahiert)
    document_date = Column(DateTime, nullable=True, index=True)  # Rechnungsdatum, Vertragsdatum etc.
    sender = Column(String(256), nullable=True, index=True)  # Absender/Firma
    reference_number = Column(String(128), nullable=True, index=True)  # Rechnungsnr., Vertragsnr. etc.
    amount = Column(Float, nullable=True)  # Rechnungsbetrag (falls Rechnung)
    
    # Verarbeitung
    page_count = Column(Integer, default=1)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Klassifikations-Reasoning
    classification_reasoning = Column(Text, nullable=True)
    
    # Sprint 1: Originalbild + Qualitätsprüfung
    original_image_path = Column(String(1024), nullable=True)  # Pfad zum Originalbild
    quality_score = Column(Float, nullable=True)  # 0-100
    quality_issues = Column(Text, nullable=True)  # JSON-Liste von Issues
    
    # Soft Delete
    deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', category='{self.category}')>"
