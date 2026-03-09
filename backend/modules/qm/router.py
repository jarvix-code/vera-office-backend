# v1.0: [QM] FastAPI Router
"""
QM-API-Endpoints.

Alle Routes werden unter /api/modules/qm/ gemountet.

Endpoints:
- GET  /dashboard         → Dashboard-Übersicht
- GET  /stats             → Sidebar-Badge
- GET  /handbook          → Handbuch-Struktur (13 Kapitel)
- GET  /handbook/{id}     → Kapitel-Details + verknüpfte Dokumente

- GET  /documents         → Liste (Filter: area, status)
- POST /documents         → Erstellen
- GET  /documents/{id}    → Detail + Revisionen
- PATCH /documents/{id}   → Update (→ neue Version!)
- DELETE /documents/{id}  → Löschen

- GET  /audits            → Liste
- POST /audits            → Erstellen (→ 10 Default-Fragen)
- GET  /audits/{id}       → Detail
- PUT  /audits/{id}/answer/{question_id} → Frage beantworten
- POST /audits/{id}/finalize → Finalisieren (→ Findings + Maßnahmen)
- GET  /audits/{id}/report → Report nach Kategorien
- DELETE /audits/{id}     → Löschen

- GET  /hygiene           → Liste
- POST /hygiene           → Erstellen (→ Default-Checkliste)
- GET  /hygiene/{id}      → Detail
- PUT  /hygiene/{id}/check → Item abhaken (→ auto-close wenn alle gecheckt)
- DELETE /hygiene/{id}    → Löschen

- GET  /compliance        → Liste (Filter: category, fulfilled)
- POST /compliance        → Erstellen
- PATCH /compliance/{id}  → Update
- DELETE /compliance/{id} → Löschen
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from loguru import logger

from backend.db.database import get_db
from .models import (
    QMDocument,
    QMDocumentRevision,
    Audit,
    AuditQuestion,
    HygieneProtocol,
    ComplianceCheck,
    QMMainArea,
    DocumentStatus,
    QMGrundelement,
    QuestionOption,
    AuditStatus,
    ProtocolStatus
)
from .schemas import (
    QMDocumentCreate,
    QMDocumentUpdate,
    QMDocumentOut,
    AuditCreate,
    AuditQuestionAnswerUpdate,
    AuditOut,
    AuditReportResponse,
    HygieneProtocolCreate,
    HygieneProtocolCheckUpdate,
    HygieneProtocolOut,
    ComplianceCheckCreate,
    ComplianceCheckUpdate,
    ComplianceCheckOut,
    DashboardResponse,
    StatsResponse
)


router = APIRouter()


# ======= HANDBUCH =======

# 13 BLZK-Kapitel (statisch)
HANDBOOK_CHAPTERS = [
    {"id": "as_01", "area": "Arbeitssicherheit", "title": "Gefährdungsbeurteilung", "order": 1},
    {"id": "as_02", "area": "Arbeitssicherheit", "title": "Betriebsanweisungen", "order": 2},
    {"id": "as_03", "area": "Arbeitssicherheit", "title": "Unterweisungen", "order": 3},
    
    {"id": "qm_01", "area": "Qualitätsmanagement", "title": "QM-Politik & Ziele", "order": 4},
    {"id": "qm_02", "area": "Qualitätsmanagement", "title": "Organisation", "order": 5},
    {"id": "qm_03", "area": "Qualitätsmanagement", "title": "Patientenversorgung", "order": 6},
    {"id": "qm_04", "area": "Qualitätsmanagement", "title": "Mitarbeiter", "order": 7},
    {"id": "qm_05", "area": "Qualitätsmanagement", "title": "Fehlermanagement", "order": 8},
    {"id": "qm_06", "area": "Qualitätsmanagement", "title": "Beschwerdemanagement", "order": 9},
    {"id": "qm_07", "area": "Qualitätsmanagement", "title": "Notfallmanagement", "order": 10},
    {"id": "qm_08", "area": "Qualitätsmanagement", "title": "Kommunikation", "order": 11},
    {"id": "qm_09", "area": "Qualitätsmanagement", "title": "Hygiene & Aufbereitung", "order": 12},
    
    {"id": "hb_01", "area": "Handbuch", "title": "Praxishandbuch Allgemein", "order": 13}
]


@router.get("/handbook")
async def get_handbook_structure():
    """
    Gibt die Handbuch-Struktur zurück (13 Kapitel).
    
    Response: Liste von Kapiteln nach Bereich gruppiert
    """
    areas = {}
    for chapter in HANDBOOK_CHAPTERS:
        area = chapter["area"]
        if area not in areas:
            areas[area] = []
        areas[area].append(chapter)
    
    return areas


@router.get("/handbook/{chapter_id}")
async def get_handbook_chapter(
    chapter_id: str,
    db: Session = Depends(get_db)
):
    """
    Gibt ein Kapitel + verknüpfte Dokumente zurück.
    
    Params:
        chapter_id: Kapitel-ID (z.B. "qm_09")
    
    Response:
        {
            "chapter": {...},
            "documents": [...]  # QM-Dokumente die dieses Kapitel betreffen
        }
    """
    chapter = next((c for c in HANDBOOK_CHAPTERS if c["id"] == chapter_id), None)
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Kapitel '{chapter_id}' nicht gefunden")
    
    # Verknüpfte Dokumente (über Tags)
    documents = db.query(QMDocument).filter(
        QMDocument.tags.contains([chapter_id])
    ).all()
    
    return {
        "chapter": chapter,
        "documents": [QMDocumentOut.from_orm(d) for d in documents]
    }


# ======= DASHBOARD =======

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Dashboard-Übersicht:
    - Dokumente (gesamt + nach Status)
    - Audits (offen + gesamt)
    - Hygiene (offen + gesamt)
    - Compliance-Rate (% erfüllt)
    """
    # Dokumente
    total_documents = db.query(QMDocument).count()
    documents_by_status = {}
    for status in DocumentStatus:
        count = db.query(QMDocument).filter(QMDocument.status == status).count()
        documents_by_status[status.value] = count
    
    # Audits
    open_audits = db.query(Audit).filter(Audit.status == AuditStatus.IN_BEARBEITUNG).count()
    total_audits = db.query(Audit).count()
    
    # Hygiene
    open_hygiene = db.query(HygieneProtocol).filter(HygieneProtocol.status == ProtocolStatus.OFFEN).count()
    total_hygiene = db.query(HygieneProtocol).count()
    
    # Compliance
    total_compliance = db.query(ComplianceCheck).count()
    fulfilled_compliance = db.query(ComplianceCheck).filter(ComplianceCheck.fulfilled == True).count()
    compliance_rate = (fulfilled_compliance / total_compliance * 100) if total_compliance > 0 else 0.0
    unfulfilled_compliance = total_compliance - fulfilled_compliance
    
    return DashboardResponse(
        total_documents=total_documents,
        documents_by_status=documents_by_status,
        open_audits=open_audits,
        total_audits=total_audits,
        open_hygiene=open_hygiene,
        total_hygiene=total_hygiene,
        compliance_rate=compliance_rate,
        unfulfilled_compliance=unfulfilled_compliance
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """
    Sidebar-Badge (offene Items).
    """
    return StatsResponse(
        documents=db.query(QMDocument).count(),
        open_audits=db.query(Audit).filter(Audit.status == AuditStatus.IN_BEARBEITUNG).count(),
        open_hygiene=db.query(HygieneProtocol).filter(HygieneProtocol.status == ProtocolStatus.OFFEN).count(),
        unfulfilled_compliance=db.query(ComplianceCheck).filter(ComplianceCheck.fulfilled == False).count()
    )


# ======= DOKUMENTE =======

@router.get("/documents", response_model=List[QMDocumentOut])
async def list_documents(
    area: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Listet QM-Dokumente mit optionalen Filtern.
    
    Query-Params:
        area: "Arbeitssicherheit" | "Qualitätsmanagement" | "Handbuch"
        status: "Entwurf" | "In Prüfung" | "Freigegeben" | "Veraltet" | "Archiviert"
        limit: Max. Anzahl (default 100)
        offset: Pagination
    """
    query = db.query(QMDocument)
    
    if area:
        matched_area = next((a for a in QMMainArea if a.value == area), None)
        if matched_area:
            query = query.filter(QMDocument.main_area == matched_area)
    
    if status:
        matched_status = next((s for s in DocumentStatus if s.value == status), None)
        if matched_status:
            query = query.filter(QMDocument.status == matched_status)
    
    documents = query.order_by(QMDocument.updated_at.desc()).limit(limit).offset(offset).all()
    return [QMDocumentOut.from_orm(d) for d in documents]


@router.post("/documents", response_model=QMDocumentOut)
async def create_document(
    doc: QMDocumentCreate,
    db: Session = Depends(get_db)
):
    """
    Erstellt ein neues QM-Dokument.
    """
    new_doc = QMDocument(
        title=doc.title,
        main_area=doc.main_area,
        content=doc.content,
        grundelemente=[g.value for g in doc.grundelemente] if doc.grundelemente else [],
        tags=doc.tags or []
    )
    
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    logger.info(f"QM-Dokument erstellt: {new_doc.title} (ID {new_doc.id})")
    return QMDocumentOut.from_orm(new_doc)


@router.get("/documents/{id}", response_model=QMDocumentOut)
async def get_document(id: int, db: Session = Depends(get_db)):
    """
    Gibt ein QM-Dokument zurück (inkl. Revisionen).
    """
    doc = db.query(QMDocument).filter(QMDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Dokument {id} nicht gefunden")
    
    return QMDocumentOut.from_orm(doc)


@router.patch("/documents/{id}", response_model=QMDocumentOut)
async def update_document(
    id: int,
    updates: QMDocumentUpdate,
    db: Session = Depends(get_db)
):
    """
    Aktualisiert ein QM-Dokument.
    
    WICHTIG: Content-Änderung → neue Version (Minor-Bump)!
    """
    doc = db.query(QMDocument).filter(QMDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Dokument {id} nicht gefunden")
    
    # Prüfe ob Content geändert wird → Versionierung
    content_changed = updates.content is not None and updates.content != doc.content
    
    if content_changed:
        # Alte Version als Revision speichern
        revision = QMDocumentRevision(
            document_id=doc.id,
            version=doc.current_version,
            content=doc.content or "",
            changelog=f"Version {doc.current_version} archiviert",
            created_at=datetime.utcnow()
        )
        db.add(revision)
        
        # Version-Bump (Minor)
        major, minor = map(int, doc.current_version.split('.'))
        doc.current_version = f"{major}.{minor + 1}"
        
        logger.info(f"Dokument {id} versioniert: {revision.version} → {doc.current_version}")
    
    # Felder aktualisieren
    if updates.title:
        doc.title = updates.title
    if updates.content is not None:
        doc.content = updates.content
    if updates.status:
        doc.status = updates.status
    if updates.grundelemente is not None:
        doc.grundelemente = [g.value for g in updates.grundelemente]
    if updates.tags is not None:
        doc.tags = updates.tags
    if updates.approved_by:
        doc.approved_by = updates.approved_by
        doc.approved_at = datetime.utcnow()
    
    doc.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(doc)
    
    return QMDocumentOut.from_orm(doc)


@router.delete("/documents/{id}")
async def delete_document(id: int, db: Session = Depends(get_db)):
    """
    Löscht ein QM-Dokument (inkl. Revisionen).
    """
    doc = db.query(QMDocument).filter(QMDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Dokument {id} nicht gefunden")
    
    db.delete(doc)
    db.commit()
    
    logger.info(f"QM-Dokument gelöscht: {doc.title} (ID {id})")
    return {"success": True, "message": f"Dokument '{doc.title}' gelöscht"}


# ======= AUDITS =======

# 10 Default-Fragen (analog zu BRAIN.md)
DEFAULT_AUDIT_QUESTIONS = [
    {"id": "hygiene_01", "text": "Wird der Hygieneplan täglich befolgt?", "category": QMGrundelement.PROZESSORIENTIERUNG},
    {"id": "patient_01", "text": "Werden Patienten über Behandlungsrisiken aufgeklärt?", "category": QMGrundelement.PATIENTENORIENTIERUNG},
    {"id": "team_01", "text": "Finden regelmäßige Teamsitzungen statt?", "category": QMGrundelement.MITARBEITERORIENTIERUNG},
    {"id": "error_01", "text": "Existiert ein funktionierendes Fehlermeldesystem?", "category": QMGrundelement.FEHLERKULTUR},
    {"id": "lead_01", "text": "Sind Verantwortlichkeiten klar definiert?", "category": QMGrundelement.FUEHRUNG},
    {"id": "comm_01", "text": "Funktioniert die interne Kommunikation effektiv?", "category": QMGrundelement.KOMMUNIKATION},
    {"id": "hygiene_02", "text": "Werden Instrumente ordnungsgemäß sterilisiert?", "category": QMGrundelement.PROZESSORIENTIERUNG},
    {"id": "patient_02", "text": "Gibt es ein Beschwerdemanagement für Patienten?", "category": QMGrundelement.PATIENTENORIENTIERUNG},
    {"id": "team_02", "text": "Werden Fortbildungen dokumentiert?", "category": QMGrundelement.MITARBEITERORIENTIERUNG},
    {"id": "safety_01", "text": "Sind Notfallpläne aktuell und zugänglich?", "category": QMGrundelement.PROZESSORIENTIERUNG}
]


@router.get("/audits", response_model=List[AuditOut])
async def list_audits(db: Session = Depends(get_db)):
    """Listet alle Audits."""
    audits = db.query(Audit).order_by(Audit.created_at.desc()).all()
    return [AuditOut.from_orm(a) for a in audits]


@router.post("/audits", response_model=AuditOut)
async def create_audit(
    audit: AuditCreate,
    db: Session = Depends(get_db)
):
    """
    Erstellt ein neues Audit.
    
    Automatisch: 10 Default-Fragen werden angelegt.
    """
    new_audit = Audit(
        title=audit.title,
        auditor=audit.auditor
    )
    
    db.add(new_audit)
    db.flush()  # Damit new_audit.id verfügbar wird
    
    # 10 Default-Fragen erstellen
    for q in DEFAULT_AUDIT_QUESTIONS:
        question = AuditQuestion(
            audit_id=new_audit.id,
            question_id=q["id"],
            question_text=q["text"],
            category=q["category"]
        )
        db.add(question)
    
    db.commit()
    db.refresh(new_audit)
    
    logger.info(f"Audit erstellt: {new_audit.title} (ID {new_audit.id})")
    return AuditOut.from_orm(new_audit)


@router.get("/audits/{id}", response_model=AuditOut)
async def get_audit(id: int, db: Session = Depends(get_db)):
    """Gibt ein Audit zurück (inkl. Fragen)."""
    audit = db.query(Audit).filter(Audit.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {id} nicht gefunden")
    
    return AuditOut.from_orm(audit)


@router.put("/audits/{id}/answer/{question_id}")
async def answer_question(
    id: int,
    question_id: str,
    answer: AuditQuestionAnswerUpdate,
    db: Session = Depends(get_db)
):
    """
    Beantwortet eine Audit-Frage.
    
    Auto-Update: completion_percentage wird neu berechnet.
    """
    audit = db.query(Audit).filter(Audit.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {id} nicht gefunden")
    
    question = db.query(AuditQuestion).filter(
        AuditQuestion.audit_id == id,
        AuditQuestion.question_id == question_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail=f"Frage '{question_id}' nicht gefunden")
    
    question.answer = answer.answer
    question.notes = answer.notes
    
    # Completion-Percentage neu berechnen
    total = len(audit.questions)
    answered = sum(1 for q in audit.questions if q.answer is not None)
    audit.completion_percentage = (answered / total) * 100 if total > 0 else 0.0
    
    db.commit()
    db.refresh(audit)
    
    logger.info(f"Audit {id} Frage {question_id} beantwortet: {answer.answer.value} ({audit.completion_percentage:.0f}%)")
    return AuditOut.from_orm(audit)


@router.post("/audits/{id}/finalize", response_model=AuditOut)
async def finalize_audit(id: int, db: Session = Depends(get_db)):
    """
    Finalisiert ein Audit.
    
    Generiert Findings + Maßnahmen aus "Nein"-Antworten.
    """
    audit = db.query(Audit).filter(Audit.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {id} nicht gefunden")
    
    # Findings aus "Nein"-Antworten generieren
    findings = []
    actions = []
    
    for q in audit.questions:
        if q.answer == QuestionOption.NEIN:
            findings.append({
                "question_id": q.question_id,
                "finding": f"Mangel festgestellt: {q.question_text}",
                "notes": q.notes
            })
            actions.append({
                "action": f"Maßnahme erforderlich für: {q.question_text}",
                "deadline": None  # TODO: Deadline aus Frontend
            })
    
    audit.findings = findings
    audit.actions = actions
    audit.status = AuditStatus.ABGESCHLOSSEN
    audit.finalized_at = datetime.utcnow()
    
    db.commit()
    db.refresh(audit)
    
    logger.success(f"Audit {id} finalisiert: {len(findings)} Findings, {len(actions)} Maßnahmen")
    return AuditOut.from_orm(audit)


@router.get("/audits/{id}/report", response_model=AuditReportResponse)
async def get_audit_report(id: int, db: Session = Depends(get_db)):
    """
    Generiert Audit-Report nach Kategorien gruppiert.
    """
    audit = db.query(Audit).filter(Audit.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {id} nicht gefunden")
    
    # Gruppierung nach Kategorien
    categories = {}
    for category in QMGrundelement:
        cat_questions = [q for q in audit.questions if q.category == category]
        answered = sum(1 for q in cat_questions if q.answer is not None)
        
        categories[category.value] = {
            "answered": answered,
            "total": len(cat_questions),
            "questions": [
                {
                    "id": q.question_id,
                    "text": q.question_text,
                    "answer": q.answer.value if q.answer else None,
                    "notes": q.notes
                }
                for q in cat_questions
            ]
        }
    
    return AuditReportResponse(
        audit_id=audit.id,
        title=audit.title,
        auditor=audit.auditor,
        finalized_at=audit.finalized_at,
        categories=categories,
        findings=audit.findings,
        actions=audit.actions
    )


@router.delete("/audits/{id}")
async def delete_audit(id: int, db: Session = Depends(get_db)):
    """Löscht ein Audit."""
    audit = db.query(Audit).filter(Audit.id == id).first()
    if not audit:
        raise HTTPException(status_code=404, detail=f"Audit {id} nicht gefunden")
    
    db.delete(audit)
    db.commit()
    
    logger.info(f"Audit gelöscht: {audit.title} (ID {id})")
    return {"success": True, "message": f"Audit '{audit.title}' gelöscht"}


# ======= HYGIENE =======

# Default-Checklisten-Items
DEFAULT_HYGIENE_ITEMS = [
    "Flächen desinfiziert",
    "Instrumente aufbereitet",
    "Handschuhe gewechselt",
    "Abfallentsorgung durchgeführt",
    "Sterilisator-Kontrolle"
]


@router.get("/hygiene", response_model=List[HygieneProtocolOut])
async def list_hygiene_protocols(db: Session = Depends(get_db)):
    """Listet Hygiene-Protokolle."""
    protocols = db.query(HygieneProtocol).order_by(HygieneProtocol.created_at.desc()).all()
    return [HygieneProtocolOut.from_orm(p) for p in protocols]


@router.post("/hygiene", response_model=HygieneProtocolOut)
async def create_hygiene_protocol(
    protocol: HygieneProtocolCreate,
    db: Session = Depends(get_db)
):
    """
    Erstellt ein neues Hygiene-Protokoll.
    
    Automatisch: Default-Checkliste wird angelegt.
    """
    checklist = [
        {"item": item, "checked": False, "timestamp": None, "notes": None}
        for item in DEFAULT_HYGIENE_ITEMS
    ]
    
    new_protocol = HygieneProtocol(
        title=protocol.title,
        area=protocol.area,
        checklist=checklist
    )
    
    db.add(new_protocol)
    db.commit()
    db.refresh(new_protocol)
    
    logger.info(f"Hygiene-Protokoll erstellt: {new_protocol.title} (ID {new_protocol.id})")
    return HygieneProtocolOut.from_orm(new_protocol)


@router.get("/hygiene/{id}", response_model=HygieneProtocolOut)
async def get_hygiene_protocol(id: int, db: Session = Depends(get_db)):
    """Gibt ein Hygiene-Protokoll zurück."""
    protocol = db.query(HygieneProtocol).filter(HygieneProtocol.id == id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail=f"Hygiene-Protokoll {id} nicht gefunden")
    
    return HygieneProtocolOut.from_orm(protocol)


@router.put("/hygiene/{id}/check")
async def check_hygiene_item(
    id: int,
    check: HygieneProtocolCheckUpdate,
    db: Session = Depends(get_db)
):
    """
    Checkt ein Item in der Hygiene-Checkliste ab.
    
    Auto-Close: Wenn alle Items gecheckt → Status = "abgeschlossen".
    """
    protocol = db.query(HygieneProtocol).filter(HygieneProtocol.id == id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail=f"Hygiene-Protokoll {id} nicht gefunden")
    
    # Item finden und abhaken
    checklist = protocol.checklist
    item_found = False
    
    for item_dict in checklist:
        if item_dict["item"] == check.item:
            item_dict["checked"] = check.checked
            item_dict["timestamp"] = datetime.utcnow().isoformat() if check.checked else None
            item_dict["notes"] = check.notes
            item_found = True
            break
    
    if not item_found:
        raise HTTPException(status_code=404, detail=f"Item '{check.item}' nicht gefunden")
    
    protocol.checklist = checklist  # Update JSON
    
    # Auto-Close wenn alle gecheckt
    all_checked = all(item["checked"] for item in checklist)
    if all_checked and protocol.status == ProtocolStatus.OFFEN:
        protocol.status = ProtocolStatus.ABGESCHLOSSEN
        protocol.closed_at = datetime.utcnow()
        logger.success(f"Hygiene-Protokoll {id} automatisch abgeschlossen")
    
    db.commit()
    db.refresh(protocol)
    
    return HygieneProtocolOut.from_orm(protocol)


@router.delete("/hygiene/{id}")
async def delete_hygiene_protocol(id: int, db: Session = Depends(get_db)):
    """Löscht ein Hygiene-Protokoll."""
    protocol = db.query(HygieneProtocol).filter(HygieneProtocol.id == id).first()
    if not protocol:
        raise HTTPException(status_code=404, detail=f"Hygiene-Protokoll {id} nicht gefunden")
    
    db.delete(protocol)
    db.commit()
    
    logger.info(f"Hygiene-Protokoll gelöscht: {protocol.title} (ID {id})")
    return {"success": True, "message": f"Hygiene-Protokoll '{protocol.title}' gelöscht"}


# ======= COMPLIANCE =======

@router.get("/compliance", response_model=List[ComplianceCheckOut])
async def list_compliance_checks(
    category: Optional[str] = None,
    fulfilled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Listet Compliance-Checks."""
    query = db.query(ComplianceCheck)
    
    if category:
        # Look up enum by value (display name) since frontend sends values like "Patientenorientierung"
        matched = next((g for g in QMGrundelement if g.value == category), None)
        if matched:
            query = query.filter(ComplianceCheck.category == matched)
    
    if fulfilled is not None:
        query = query.filter(ComplianceCheck.fulfilled == fulfilled)
    
    checks = query.order_by(ComplianceCheck.due_date).all()
    return [ComplianceCheckOut.from_orm(c) for c in checks]


@router.post("/compliance", response_model=ComplianceCheckOut)
async def create_compliance_check(
    check: ComplianceCheckCreate,
    db: Session = Depends(get_db)
):
    """Erstellt einen Compliance-Check."""
    new_check = ComplianceCheck(
        title=check.title,
        category=check.category,
        requirement=check.requirement,
        due_date=check.due_date
    )
    
    db.add(new_check)
    db.commit()
    db.refresh(new_check)
    
    logger.info(f"Compliance-Check erstellt: {new_check.title} (ID {new_check.id})")
    return ComplianceCheckOut.from_orm(new_check)


@router.patch("/compliance/{id}", response_model=ComplianceCheckOut)
async def update_compliance_check(
    id: int,
    updates: ComplianceCheckUpdate,
    db: Session = Depends(get_db)
):
    """Aktualisiert einen Compliance-Check."""
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == id).first()
    if not check:
        raise HTTPException(status_code=404, detail=f"Compliance-Check {id} nicht gefunden")
    
    if updates.title:
        check.title = updates.title
    if updates.fulfilled is not None:
        check.fulfilled = updates.fulfilled
    if updates.evidence:
        check.evidence = updates.evidence
    if updates.due_date:
        check.due_date = updates.due_date
    
    check.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(check)
    
    return ComplianceCheckOut.from_orm(check)


@router.delete("/compliance/{id}")
async def delete_compliance_check(id: int, db: Session = Depends(get_db)):
    """Löscht einen Compliance-Check."""
    check = db.query(ComplianceCheck).filter(ComplianceCheck.id == id).first()
    if not check:
        raise HTTPException(status_code=404, detail=f"Compliance-Check {id} nicht gefunden")
    
    db.delete(check)
    db.commit()
    
    logger.info(f"Compliance-Check gelöscht: {check.title} (ID {id})")
    return {"success": True, "message": f"Compliance-Check '{check.title}' gelöscht"}


# ============================================================
# BLZK Dokumentenkatalog + Fristen (Phase 1 Grundstruktur)
# ============================================================

@router.get("/blzk/katalog")
async def get_blzk_katalog():
    """Gibt den kompletten BLZK-Dokumentenkatalog zurück."""
    from .blzk import get_all_documents, get_fristen
    return {
        "dokumente": get_all_documents(),
        "fristen": get_fristen(),
        "total": len(get_all_documents())
    }

@router.get("/blzk/fristen")
async def get_blzk_fristen():
    """Gibt den BLZK Fristen-Kalender zurück (täglich/halbjährlich/jährlich/mehrjährlich)."""
    from .blzk import get_fristen
    fristen = get_fristen()
    return {
        "taeglich": fristen.get("taeglich", []),
        "halbjaehrlich": fristen.get("halbjaehrlich", []),
        "jaehrlich": fristen.get("jaehrlich", []),
        "mehrjaehrlich": fristen.get("mehrjaehrlich", [])
    }

@router.get("/blzk/dokument/{code}")
async def get_blzk_dokument(code: str):
    """Gibt ein einzelnes BLZK-Dokument anhand seines Codes zurück."""
    from .blzk import get_document_by_code
    doc = get_document_by_code(code)
    if not doc:
        raise HTTPException(status_code=404, detail=f"BLZK-Code {code} nicht gefunden")
    return doc
