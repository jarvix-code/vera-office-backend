# v1.0: [QM] SQLAlchemy Models
"""
QM-Modelle: BLZK-konformes Qualitätsmanagement.

Tabellen:
- qm_documents: Versionierte QM-Dokumente (13 BLZK-Kapitel)
- qm_audits: Interne Audits mit Fragenkatalog
- qm_audit_questions: Fragen eines Audits (10 Default-Fragen)
- qm_hygiene_protocols: Tägliche/wöchentliche Hygiene-Checklisten
- qm_compliance_checks: Compliance-Nachweise

Versionskonzept:
- Jede Änderung an QM-Dokumenten -> neue Version (Major.Minor)
- Revisionen in separater Tabelle (qm_document_revisions)
"""

from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ======= ENUMS =======

class QMMainArea(PyEnum):
    """BLZK-Hauptbereiche."""
    ARBEITSSICHERHEIT = "Arbeitssicherheit"
    QUALITAETSMANAGEMENT = "Qualitätsmanagement"
    HANDBUCH = "Handbuch"


class DocumentStatus(PyEnum):
    """Dokumenten-Status (Freigabe-Workflow)."""
    ENTWURF = "Entwurf"
    PRUEFUNG = "In Prüfung"
    FREIGEGEBEN = "Freigegeben"
    VERALTET = "Veraltet"
    ARCHIVIERT = "Archiviert"


class QMGrundelement(PyEnum):
    """6 Grundelemente nach G-BA QM-Richtlinie."""
    PATIENTENORIENTIERUNG = "Patientenorientierung"
    MITARBEITERORIENTIERUNG = "Mitarbeiterorientierung"
    PROZESSORIENTIERUNG = "Prozessorientierung"
    FUEHRUNG = "Führung und Verantwortung"
    FEHLERKULTUR = "Fehlerkultur"
    KOMMUNIKATION = "Kommunikation"


class QuestionOption(PyEnum):
    """Antwort-Optionen für Audit-Fragen."""
    JA = "Ja"
    NEIN = "Nein"
    UEBERSPRINGEN = "Überspringen"


class AuditStatus(PyEnum):
    """Status eines Audits."""
    IN_BEARBEITUNG = "In Bearbeitung"
    ABGESCHLOSSEN = "Abgeschlossen"


class ProtocolStatus(PyEnum):
    """Status eines Hygiene-Protokolls."""
    OFFEN = "offen"
    ABGESCHLOSSEN = "abgeschlossen"


# ======= MODELS =======

class QMDocument(Base):
    """
    QM-Dokument (z.B. Hygieneplan, Dienstvertrag, Arbeitsanweisung).
    
    Features:
    - Versionierung (current_version = "1.2")
    - Freigabe-Workflow (Entwurf -> Prüfung -> Freigegeben)
    - Verknüpfung zu BLZK-Hauptbereichen
    - Tags für Grundelemente
    """
    __tablename__ = "qm_documents"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Metadaten
    title = Column(String(255), nullable=False)
    main_area = Column(Enum(QMMainArea), nullable=False, index=True)
    content = Column(Text, nullable=True)  # Markdown-Format
    
    # Versionierung
    current_version = Column(String(20), nullable=False, default="1.0")
    
    # Status
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.ENTWURF, index=True)
    
    # Freigabe
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Tags (JSON-Array von Grundelementen)
    grundelemente = Column(JSON, nullable=True, default=list)
    tags = Column(JSON, nullable=True, default=list)  # Zusätzliche Custom-Tags
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationen
    revisions = relationship("QMDocumentRevision", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<QMDocument(id={self.id}, title={self.title}, v={self.current_version})>"


class QMDocumentRevision(Base):
    """
    Versionsverlauf eines QM-Dokuments.
    
    Jede Änderung an QMDocument.content -> neuer Revision-Eintrag.
    """
    __tablename__ = "qm_document_revisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("qm_documents.id"), nullable=False, index=True)
    
    version = Column(String(20), nullable=False)  # z.B. "1.1"
    content = Column(Text, nullable=False)
    changelog = Column(Text, nullable=True)  # Was wurde geändert?
    
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relation
    document = relationship("QMDocument", back_populates="revisions")
    
    def __repr__(self):
        return f"<Revision(doc_id={self.document_id}, v={self.version})>"


class Audit(Base):
    """
    Internes Audit gemäß QM-Richtlinie.
    
    Workflow:
    1. Audit erstellen -> 10 Default-Fragen werden generiert
    2. Fragen beantworten (Ja/Nein/Überspringen)
    3. Finalisieren -> Findings + Maßnahmen aus "Nein"-Antworten
    4. Report exportieren
    """
    __tablename__ = "qm_audits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(255), nullable=False)
    auditor = Column(String(100), nullable=False)
    
    status = Column(Enum(AuditStatus), nullable=False, default=AuditStatus.IN_BEARBEITUNG, index=True)
    completion_percentage = Column(Float, nullable=False, default=0.0)
    
    # JSON-Arrays (für schnellen Zugriff)
    findings = Column(JSON, nullable=True, default=list)  # [{"question_id": "...", "finding": "..."}]
    actions = Column(JSON, nullable=True, default=list)   # [{"action": "...", "deadline": "..."}]
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finalized_at = Column(DateTime, nullable=True)
    
    # Relationen
    questions = relationship("AuditQuestion", back_populates="audit", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Audit(id={self.id}, title={self.title}, {self.completion_percentage:.0f}%)>"


class AuditQuestion(Base):
    """
    Eine Frage innerhalb eines Audits.
    
    10 Default-Fragen werden bei Audit-Erstellung automatisch angelegt.
    """
    __tablename__ = "qm_audit_questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(Integer, ForeignKey("qm_audits.id"), nullable=False, index=True)
    
    question_id = Column(String(50), nullable=False)  # z.B. "hygiene_01"
    question_text = Column(Text, nullable=False)
    category = Column(Enum(QMGrundelement), nullable=False)
    
    answer = Column(Enum(QuestionOption), nullable=True)  # Ja/Nein/Überspringen
    notes = Column(Text, nullable=True)
    
    # Relation
    audit = relationship("Audit", back_populates="questions")
    
    def __repr__(self):
        return f"<AuditQuestion(id={self.question_id}, answer={self.answer})>"


class HygieneProtocol(Base):
    """
    Hygiene-Checkliste (täglich/wöchentlich).
    
    Features:
    - Default-Items (Desinfektion, Sterilisation, etc.)
    - Abhaken mit Zeitstempel
    - Auto-Close wenn alle Items gecheckt
    """
    __tablename__ = "qm_hygiene_protocols"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(255), nullable=False)
    area = Column(String(100), nullable=True)  # z.B. "Behandlungsraum 1"
    
    # Checkliste (JSON-Array)
    # [{"item": "Flächen desinfiziert", "checked": true, "timestamp": "...", "notes": "..."}]
    checklist = Column(JSON, nullable=False, default=list)
    
    status = Column(Enum(ProtocolStatus), nullable=False, default=ProtocolStatus.OFFEN, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<HygieneProtocol(id={self.id}, title={self.title}, status={self.status.value})>"


class ComplianceCheck(Base):
    """
    Compliance-Nachweis.
    
    Zeigt pro Grundelement ob Anforderungen erfüllt sind.
    """
    __tablename__ = "qm_compliance_checks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(255), nullable=False)
    category = Column(Enum(QMGrundelement), nullable=False, index=True)
    
    requirement = Column(Text, nullable=False)  # Was ist gefordert?
    fulfilled = Column(Boolean, nullable=False, default=False)
    evidence = Column(Text, nullable=True)  # Nachweis (z.B. Dokument-ID)
    
    due_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ComplianceCheck(id={self.id}, fulfilled={self.fulfilled})>"
