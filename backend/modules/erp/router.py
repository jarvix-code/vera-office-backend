# v1.0: [ERP] FastAPI Router
"""
ERP-API-Endpoints.

Alle Routes werden unter /api/modules/erp/ gemountet.

Endpoints:
- GET  /items             → Liste (Filter: direction, status, counterparty, start/end)
- GET  /items/{id}        → Einzelner Record
- POST /items             → Neuen Record anlegen (auto-berechnet MwSt/Brutto)
- PATCH /items/{id}       → Update
- DELETE /items/{id}      → Löschen
- GET  /dashboard         → Aggregiertes Dashboard
- GET  /reports/bwa       → BWA-Report
- GET  /reports/ust       → USt-Voranmeldung
- GET  /reports/csv       → CSV-Download
- GET  /reports/datev     → DATEV-Buchungsstapel
- GET  /open-items        → Offene Posten mit Ampel
- GET  /stats             → Sidebar-Badge (total, open, overdue)
"""

from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from loguru import logger

from backend.db.database import get_db
from .models import FinancialRecord, Direction, PaymentStatus
from .schemas import (
    FinancialRecordCreate,
    FinancialRecordUpdate,
    FinancialRecordOut,
    DashboardResponse,
    BWAResponse,
    UStResponse,
    OpenItemResponse,
    StatsResponse
)
from .calculator import calculate_dashboard, calculate_bwa, calculate_ust
from .reports import export_csv, export_datev


router = APIRouter()


# ======= CRUD =======

@router.get("/items", response_model=List[FinancialRecordOut])
async def list_items(
    direction: Optional[str] = None,
    status: Optional[str] = None,
    counterparty: Optional[str] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Listet Financial Records mit optionalen Filtern.
    
    Query-Params:
        direction: "incoming" | "outgoing"
        status: "open" | "paid" | "overdue"
        counterparty: Lieferant/Kunde (Substring-Match)
        start: Datum ab (ISO)
        end: Datum bis (ISO)
        limit: Max. Anzahl (default 100, max 1000)
        offset: Pagination
    """
    query = db.query(FinancialRecord)
    
    if direction:
        query = query.filter(FinancialRecord.direction == Direction[direction.upper()])
    
    if status:
        query = query.filter(FinancialRecord.payment_status == PaymentStatus[status.upper()])
    
    if counterparty:
        query = query.filter(FinancialRecord.counterparty.ilike(f'%{counterparty}%'))
    
    if start:
        query = query.filter(FinancialRecord.invoice_date >= start)
    
    if end:
        query = query.filter(FinancialRecord.invoice_date <= end)
    
    records = query.order_by(FinancialRecord.invoice_date.desc()).offset(offset).limit(limit).all()
    
    return [_record_to_out(r) for r in records]


@router.get("/items/{item_id}", response_model=FinancialRecordOut)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Gibt einzelnen Record zurück."""
    record = db.query(FinancialRecord).filter(FinancialRecord.id == item_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record nicht gefunden")
    
    return _record_to_out(record)


@router.post("/items", response_model=FinancialRecordOut, status_code=201)
async def create_item(item: FinancialRecordCreate, db: Session = Depends(get_db)):
    """
    Erstellt neuen Record.
    Auto-Berechnung: Wenn nur netto ODER brutto gegeben → anderer Wert wird berechnet.
    """
    # Auto-Berechnung Netto ↔ Brutto
    net = item.net_amount
    gross = item.gross_amount
    vat_rate = item.vat_rate
    
    if net and not gross:
        vat_amount = net * vat_rate / 100
        gross = net + vat_amount
    elif gross and not net:
        net = gross / (1 + vat_rate / 100)
        vat_amount = gross - net
    elif net and gross:
        vat_amount = gross - net
    else:
        raise HTTPException(
            status_code=400,
            detail="Entweder net_amount oder gross_amount muss angegeben werden"
        )
    
    # Record erstellen
    record = FinancialRecord(
        document_id=item.document_id,
        direction=Direction[item.direction.upper()],
        invoice_number=item.invoice_number,
        invoice_date=item.invoice_date,
        due_date=item.due_date,
        net_amount=round(net, 2),
        vat_rate=vat_rate,
        vat_amount=round(vat_amount, 2),
        gross_amount=round(gross, 2),
        counterparty=item.counterparty,
        category=item.category,
        payment_status=PaymentStatus.OPEN,
        notes=item.notes
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    logger.info(f"Record erstellt: {record.id} | {record.direction.value} | {record.gross_amount}€")
    
    return _record_to_out(record)


@router.patch("/items/{item_id}", response_model=FinancialRecordOut)
async def update_item(
    item_id: int,
    update: FinancialRecordUpdate,
    db: Session = Depends(get_db)
):
    """Updatet einen Record (nur angegebene Felder)."""
    record = db.query(FinancialRecord).filter(FinancialRecord.id == item_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record nicht gefunden")
    
    # Update-Felder
    update_data = update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if key == 'payment_status' and value:
            value = PaymentStatus[value.upper()]
        setattr(record, key, value)
    
    # Auto-Berechnung wenn Beträge geändert
    if any(k in update_data for k in ['net_amount', 'gross_amount', 'vat_rate']):
        net = record.net_amount
        gross = record.gross_amount
        vat_rate = record.vat_rate
        
        if net:
            vat_amount = net * vat_rate / 100
            gross = net + vat_amount
        elif gross:
            net = gross / (1 + vat_rate / 100)
            vat_amount = gross - net
        
        record.net_amount = round(net, 2)
        record.vat_amount = round(vat_amount, 2)
        record.gross_amount = round(gross, 2)
    
    db.commit()
    db.refresh(record)
    
    logger.info(f"Record aktualisiert: {record.id}")
    
    return _record_to_out(record)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Löscht einen Record."""
    record = db.query(FinancialRecord).filter(FinancialRecord.id == item_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record nicht gefunden")
    
    db.delete(record)
    db.commit()
    
    logger.info(f"Record gelöscht: {item_id}")
    
    return Response(status_code=204)


# ======= Dashboard & Reports =======

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    start: date = Query(..., description="Perioden-Start"),
    end: date = Query(..., description="Perioden-Ende"),
    db: Session = Depends(get_db)
):
    """
    Dashboard-Daten (Brutto-basiert).
    Default: Jahresbeginn bis heute (Frontend sollte das setzen).
    """
    return calculate_dashboard(db, start, end)


@router.get("/reports/bwa", response_model=BWAResponse)
async def get_bwa(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db)
):
    """BWA-Report (Netto-basiert, mit Periodenvergleich)."""
    return calculate_bwa(db, start, end)


@router.get("/reports/ust", response_model=UStResponse)
async def get_ust(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db)
):
    """USt-Voranmeldung (Output VAT - Input VAT)."""
    return calculate_ust(db, start, end)


@router.get("/reports/csv")
async def download_csv(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db)
):
    """CSV-Export (Semikolon-getrennt, UTF-8)."""
    csv_data = export_csv(db, start, end)
    
    filename = f"vera_erp_{start.isoformat()}_{end.isoformat()}.csv"
    
    return Response(
        content=csv_data,
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@router.get("/reports/datev")
async def download_datev(
    start: date = Query(...),
    end: date = Query(...),
    berater_nr: int = Query(..., description="DATEV Berater-Nummer"),
    mandanten_nr: int = Query(..., description="DATEV Mandanten-Nummer"),
    db: Session = Depends(get_db)
):
    """DATEV Buchungsstapel v700 (cp1252, SKR03)."""
    datev_data = export_datev(db, start, end, berater_nr, mandanten_nr)
    
    filename = f"EXTF_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
    
    return Response(
        content=datev_data,
        media_type='text/csv; charset=windows-1252',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# ======= Open Items =======

@router.get("/open-items", response_model=List[OpenItemResponse])
async def get_open_items(
    direction: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Offene Posten mit Ampel-System.
    
    Ampel:
        🟢 Grün: >7 Tage bis Fälligkeit
        🟡 Gelb: ≤7 Tage bis Fälligkeit
        🔴 Rot: Überfällig
    """
    query = db.query(FinancialRecord).filter(
        FinancialRecord.payment_status == PaymentStatus.OPEN
    )
    
    if direction:
        query = query.filter(FinancialRecord.direction == Direction[direction.upper()])
    
    records = query.order_by(FinancialRecord.due_date).all()
    
    today = date.today()
    items = []
    
    for r in records:
        # Tage bis Fälligkeit
        if r.due_date:
            days_until_due = (r.due_date - today).days
        else:
            days_until_due = None
        
        # Ampel-Status
        if days_until_due is None:
            color = "yellow"  # Kein Fälligkeitsdatum
        elif days_until_due < 0:
            color = "red"  # Überfällig
        elif days_until_due <= 7:
            color = "yellow"  # Bald fällig
        else:
            color = "green"  # Noch Zeit
        
        items.append(OpenItemResponse(
            id=r.id,
            direction=r.direction.value,
            invoice_number=r.invoice_number,
            invoice_date=r.invoice_date,
            due_date=r.due_date,
            gross_amount=r.gross_amount,
            counterparty=r.counterparty,
            days_until_due=days_until_due,
            status_color=color
        ))
    
    return items


# ======= Stats =======

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Statistiken für Sidebar-Badge."""
    total = db.query(FinancialRecord).count()
    open_count = db.query(FinancialRecord).filter(
        FinancialRecord.payment_status == PaymentStatus.OPEN
    ).count()
    
    # Überfällige = Fälligkeit < heute UND status = open
    today = date.today()
    overdue = db.query(FinancialRecord).filter(
        FinancialRecord.payment_status == PaymentStatus.OPEN,
        FinancialRecord.due_date < today
    ).count()
    
    return StatsResponse(
        total=total,
        open=open_count,
        overdue=overdue
    )


# ======= Helpers =======

def _record_to_out(record: FinancialRecord) -> FinancialRecordOut:
    """Konvertiert SQLAlchemy Model zu Pydantic Schema."""
    return FinancialRecordOut(
        id=record.id,
        document_id=record.document_id,
        direction=record.direction.value,
        invoice_number=record.invoice_number,
        invoice_date=record.invoice_date,
        due_date=record.due_date,
        net_amount=record.net_amount,
        vat_rate=record.vat_rate,
        vat_amount=record.vat_amount,
        gross_amount=record.gross_amount,
        counterparty=record.counterparty,
        category=record.category,
        payment_status=record.payment_status.value,
        payment_date=record.payment_date,
        notes=record.notes,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat()
    )
