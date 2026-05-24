"""
VERA Office - Document Model
Repräsentiert ein verarbeitetes Dokument in der Datenbank
"""
import re
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy import types
from sqlalchemy.orm import relationship, validates
from backend.db.database import Base

_GERMAN_DATE_RE = re.compile(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$')


def _parse_flexible_datetime(value):
    """Parst datetime-Werte: ISO 8601 und deutsches DD.MM.YYYY Format."""
    if value is None or isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return value
    val = value.strip()
    # ISO 8601 zuerst versuchen
    try:
        return datetime.fromisoformat(val)
    except ValueError:
        pass
    # Deutsches Format: DD.MM.YYYY [HH:MM[:SS]]
    m = _GERMAN_DATE_RE.match(val)
    if m:
        d, mo, y, h, mi, s = m.groups()
        h = int(h) if h else 0
        mi = int(mi) if mi else 0
        s = int(s) if s else 0
        year = int(y)
        if year < 100:
            year = 2000 + year if year < 50 else 1900 + year
        try:
            return datetime(year, int(mo), int(d), h, mi, s)
        except ValueError:
            pass
    return None


class FlexibleDateTime(types.TypeDecorator):
    """
    SQLAlchemy TypeDecorator für DateTime.
    Akzeptiert beim Lesen aus SQLite sowohl ISO 8601 als auch DD.MM.YYYY Strings.
    Verhindert ValueError: Invalid isoformat string bei alten Einträgen.
    """
    impl = types.DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        """Wird beim Lesen aus der DB aufgerufen."""
        if value is None:
            return value
        if isinstance(value, datetime):
            return value
        return _parse_flexible_datetime(value)

    def process_bind_param(self, value, dialect):
        """Wird beim Schreiben in die DB aufgerufen — normalisiert zu datetime."""
        if value is None:
            return value
        if isinstance(value, str):
            value = _parse_flexible_datetime(value)
        return value


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
    document_date = Column(FlexibleDateTime, nullable=True, index=True)  # Rechnungsdatum, Vertragsdatum etc.
    sender = Column(String(256), nullable=True, index=True)  # Absender/Firma
    reference_number = Column(String(128), nullable=True, index=True)  # Rechnungsnr., Vertragsnr. etc.
    amount = Column(Float, nullable=True)  # Rechnungsbetrag (falls Rechnung)
    
    # Verarbeitung
    page_count = Column(Integer, default=1)
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(FlexibleDateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(FlexibleDateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Klassifikations-Reasoning & Status
    classification_reasoning = Column(Text, nullable=True)
    classification_status = Column(String(50), nullable=True, default="pending", index=True)
    # Status values:
    # - "pending": Noch nicht klassifiziert
    # - "auto_classified": Automatisch klassifiziert (Confidence >= threshold)
    # - "user_confirmed": User hat klassifiziert/bestätigt
    # - "needs_user_help": VERA unsicher, braucht User-Hilfe (Active Learning)
    # - "needs_dev_review": User + VERA unsicher → Developer Queue
    # - "dev_reviewed": Developer hat reviewt
    # - "dev_skipped": Developer hat übersprungen
    # - "ocr_problem": OCR-Qualitätsproblem
    # - "training_data": Für Training markiert
    # - "processing": OCR/Verarbeitung läuft noch
    
    # Active Learning Fields (Boris' Feedback 2026-03-28)
    user_explanation = Column(Text, nullable=True)  # User's free-text explanation
    classified_at = Column(FlexibleDateTime, nullable=True)  # When was it classified?
    confidence = Column(Float, nullable=True)  # Classification confidence (0.0-1.0)
    
    # Escalation Fields
    user_comment = Column(Text, nullable=True)  # User comment when escalating
    escalated_at = Column(FlexibleDateTime, nullable=True)  # When was it escalated?
    escalated_by = Column(String(128), nullable=True)  # Who escalated it?
    reviewed_at = Column(FlexibleDateTime, nullable=True)  # When was it reviewed by dev?
    dev_notes = Column(Text, nullable=True)  # Developer notes
    
    # Sprint 1: Originalbild + Qualitätsprüfung
    original_image_path = Column(String(1024), nullable=True)  # Pfad zum Originalbild
    quality_score = Column(Float, nullable=True)  # 0-100
    quality_issues = Column(Text, nullable=True)  # JSON-Liste von Issues
    # Bug #720 / #719: Invoice validation result (workflow_engine + invoice-check endpoint)
    invoice_validation = Column(String(50), nullable=True)  # 'valid' | 'incomplete' | None
    
    # Soft Delete
    deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(FlexibleDateTime, nullable=True)

    @validates('document_date', 'classified_at', 'escalated_at', 'reviewed_at', 'deleted_at')
    def validate_datetime_fields(self, key, value):
        """Konvertiert deutsche Datumsstrings (DD.MM.YYYY) vor dem Speichern in ISO datetime."""
        if isinstance(value, str):
            parsed = _parse_flexible_datetime(value)
            if isinstance(parsed, datetime):
                return parsed
        return value

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', category='{self.category}')>"
