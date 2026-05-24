"""
VERA Office - QM Models
SQLAlchemy models for QM documents, audits, hygiene protocols.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.database import Base


class QMDocument(Base):
    """QM-Dokument (Handbuch, Prozessbeschreibung, Arbeitsanweisung)."""
    __tablename__ = "qm_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    main_area = Column(String(100))  # Arbeitssicherheit, Qualitätsmanagement, Handbuch
    content = Column(Text)
    status = Column(String(50), default="Entwurf")  # Entwurf, In Prüfung, Freigegeben, Veraltet, Archiviert
    current_version = Column(String(20), default="1.0")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # NEW: OCR + File Storage (Universal für alle VERA-Dokumente!)
    file_path = Column(String(500))  # Pfad zur PDF-Datei
    ocr_text = Column(Text)  # OCR-extrahierter Text für schnelle Suche
    
    # Relations
    revisions = relationship("QMDocumentRevision", back_populates="document", cascade="all, delete-orphan")


class QMDocumentRevision(Base):
    """Revisionsverlauf für QM-Dokumente."""
    __tablename__ = "qm_document_revisions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("qm_documents.id"), nullable=False)
    version = Column(String(20), nullable=False)
    change_summary = Column(String(500))
    content_snapshot = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer)  # User ID
    
    # Relations
    document = relationship("QMDocument", back_populates="revisions")


class QMAudit(Base):
    """Internes Audit."""
    __tablename__ = "qm_audits"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    area = Column(String(100))  # z.B. "Hygiene", "Patientenversorgung"
    scheduled_date = Column(DateTime)
    completed_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="Offen")  # Offen, In Bearbeitung, Abgeschlossen
    findings = Column(Text)  # JSON-Array mit Feststellungen
    created_at = Column(DateTime, default=datetime.now)
    
    # Relations
    questions = relationship("QMAuditQuestion", back_populates="audit", cascade="all, delete-orphan")


class QMAuditQuestion(Base):
    """Audit-Frage."""
    __tablename__ = "qm_audit_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey("qm_audits.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    compliant = Column(Boolean, nullable=True)  # True = konform, False = Abweichung
    evidence = Column(String(500), nullable=True)  # Nachweis/Dokumentation
    
    # Relations
    audit = relationship("QMAudit", back_populates="questions")


class QMHygieneProtocol(Base):
    """Hygiene-Protokoll (täglich/wöchentlich)."""
    __tablename__ = "qm_hygiene_protocols"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    frequency = Column(String(50))  # täglich, wöchentlich, monatlich
    checklist = Column(JSON)  # Array of {item, checked, checked_by, timestamp}
    status = Column(String(50), default="Offen")  # Offen, Abgeschlossen
    completed_by = Column(Integer)  # User ID
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class QMComplianceCheck(Base):
    """Compliance-Check (BLZK-Anforderungen)."""
    __tablename__ = "qm_compliance_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    requirement = Column(String(500), nullable=False)
    category = Column(String(100))  # z.B. "Hygiene", "Dokumentation"
    fulfilled = Column(Boolean, default=False)
    evidence = Column(String(500), nullable=True)
    checked_date = Column(DateTime, nullable=True)
    next_check = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
