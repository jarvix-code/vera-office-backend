# v1.0: [QM] Pydantic Schemas
"""
Request/Response-Schemas für QM-API.

Naming-Convention:
- {Model}Create: Request-Body für POST
- {Model}Update: Request-Body für PATCH
- {Model}Out: Response für GET (inkl. Timestamps)
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .models import (
    QMMainArea,
    DocumentStatus,
    QMGrundelement,
    QuestionOption,
    AuditStatus,
    ProtocolStatus
)


# ======= QM-Dokumente =======

class QMDocumentCreate(BaseModel):
    """Request: Neues QM-Dokument erstellen."""
    title: str
    main_area: QMMainArea
    content: Optional[str] = None
    grundelemente: Optional[List[QMGrundelement]] = []
    tags: Optional[List[str]] = []


class QMDocumentUpdate(BaseModel):
    """Request: QM-Dokument aktualisieren (-> neue Version)."""
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[DocumentStatus] = None
    grundelemente: Optional[List[QMGrundelement]] = None
    tags: Optional[List[str]] = None
    approved_by: Optional[str] = None


class QMDocumentRevisionOut(BaseModel):
    """Response: Eine Revision."""
    id: int
    version: str
    content: str
    changelog: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class QMDocumentOut(BaseModel):
    """Response: QM-Dokument (inkl. Revisionen)."""
    id: int
    title: str
    main_area: QMMainArea
    content: Optional[str] = None
    current_version: str
    status: DocumentStatus
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    grundelemente: List[QMGrundelement]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    revisions: List[QMDocumentRevisionOut] = []
    
    class Config:
        from_attributes = True


# ======= Audits =======

class AuditCreate(BaseModel):
    """Request: Neues Audit erstellen."""
    title: str
    auditor: str


class AuditQuestionAnswerUpdate(BaseModel):
    """Request: Audit-Frage beantworten."""
    answer: QuestionOption
    notes: Optional[str] = None


class AuditQuestionOut(BaseModel):
    """Response: Audit-Frage."""
    id: int
    question_id: str
    question_text: str
    category: QMGrundelement
    answer: Optional[QuestionOption] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class AuditOut(BaseModel):
    """Response: Audit (inkl. Fragen)."""
    id: int
    title: str
    auditor: str
    status: AuditStatus
    completion_percentage: float
    findings: List[dict] = []
    actions: List[dict] = []
    created_at: datetime
    finalized_at: Optional[datetime] = None
    questions: List[AuditQuestionOut] = []
    
    class Config:
        from_attributes = True


class AuditReportResponse(BaseModel):
    """Response: Audit-Report gruppiert nach Kategorien."""
    audit_id: int
    title: str
    auditor: str
    finalized_at: Optional[datetime] = None
    categories: dict  # {kategorie: {answered: X, total: Y, questions: [...]}}
    findings: List[dict] = []
    actions: List[dict] = []


# ======= Hygiene =======

class ChecklistItem(BaseModel):
    """Ein Item in einer Hygiene-Checkliste."""
    item: str
    checked: bool = False
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None


class HygieneProtocolCreate(BaseModel):
    """Request: Neues Hygiene-Protokoll erstellen."""
    title: str
    area: Optional[str] = None


class HygieneProtocolCheckUpdate(BaseModel):
    """Request: Item abhaken."""
    item: str  # Item-Name
    checked: bool
    notes: Optional[str] = None


class HygieneProtocolOut(BaseModel):
    """Response: Hygiene-Protokoll."""
    id: int
    title: str
    area: Optional[str] = None
    checklist: List[ChecklistItem]
    status: ProtocolStatus
    created_at: datetime
    closed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ======= Compliance =======

class ComplianceCheckCreate(BaseModel):
    """Request: Neuer Compliance-Check."""
    title: str
    category: QMGrundelement
    requirement: str
    due_date: Optional[date] = None


class ComplianceCheckUpdate(BaseModel):
    """Request: Compliance-Check aktualisieren."""
    title: Optional[str] = None
    fulfilled: Optional[bool] = None
    evidence: Optional[str] = None
    due_date: Optional[date] = None


class ComplianceCheckOut(BaseModel):
    """Response: Compliance-Check."""
    id: int
    title: str
    category: QMGrundelement
    requirement: str
    fulfilled: bool
    evidence: Optional[str] = None
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ======= Dashboard =======

class DashboardResponse(BaseModel):
    """Response: QM-Dashboard."""
    total_documents: int
    documents_by_status: dict  # {status: count}
    open_audits: int
    total_audits: int
    open_hygiene: int
    total_hygiene: int
    compliance_rate: float  # % erfüllter Checks
    unfulfilled_compliance: int


class StatsResponse(BaseModel):
    """Response: Sidebar-Badge (offene Items)."""
    documents: int
    open_audits: int
    open_hygiene: int
    unfulfilled_compliance: int
