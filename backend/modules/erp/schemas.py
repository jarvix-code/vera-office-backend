# v1.0: [ERP] Pydantic Schemas
"""
Request/Response Schemas für ERP-API.

Kategorien:
- CRUD: FinancialRecordCreate, Update, Out
- Dashboard: DashboardResponse, MonthlyStats
- Reports: BWAResponse, UStResponse
- Open Items: OpenItemResponse
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ======= CRUD Schemas =======

class FinancialRecordCreate(BaseModel):
    """Schema zum Erstellen eines Records."""
    document_id: Optional[str] = None
    direction: str  # "incoming" | "outgoing"
    invoice_number: Optional[str] = None
    invoice_date: date
    due_date: Optional[date] = None
    net_amount: Optional[float] = None
    vat_rate: float = 19.0
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    counterparty: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    
    @field_validator('direction')
    def validate_direction(cls, v):
        if v not in ['incoming', 'outgoing']:
            raise ValueError("direction muss 'incoming' oder 'outgoing' sein")
        return v


class FinancialRecordUpdate(BaseModel):
    """Schema zum Updaten eines Records (alle Felder optional)."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    net_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    counterparty: Optional[str] = None
    category: Optional[str] = None
    payment_status: Optional[str] = None  # "open" | "paid" | "overdue"
    payment_date: Optional[date] = None
    notes: Optional[str] = None


class FinancialRecordOut(BaseModel):
    """Schema für API-Response."""
    id: int
    document_id: Optional[str]
    direction: str
    invoice_number: Optional[str]
    invoice_date: date
    due_date: Optional[date]
    net_amount: float
    vat_rate: float
    vat_amount: float
    gross_amount: float
    counterparty: Optional[str]
    category: Optional[str]
    payment_status: str
    payment_date: Optional[date]
    notes: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


# ======= Dashboard Schemas =======

class MonthlyStats(BaseModel):
    """Statistiken für einen Monat."""
    month: str  # Format: "YYYY-MM"
    revenue: float
    expenses: float
    profit: float


class CategoryBreakdown(BaseModel):
    """Ausgaben nach Kategorie."""
    category: str
    amount: float


class TopCounterparty(BaseModel):
    """Top Lieferanten/Kunden."""
    name: str
    amount: float


class PeriodComparison(BaseModel):
    """Vergleich aktuelle vs. vorherige Periode."""
    current: float
    previous: float
    delta: float
    delta_pct: float


class DashboardResponse(BaseModel):
    """Dashboard-Daten."""
    total_revenue: float
    total_expenses: float
    total_profit: float
    monthly: list[MonthlyStats]
    categories: list[CategoryBreakdown]
    top_suppliers: list[TopCounterparty]
    top_customers: list[TopCounterparty]
    comparison: Optional[PeriodComparison] = None


# ======= BWA Schemas =======

class BWARow(BaseModel):
    """Eine Zeile in der BWA."""
    label: str
    current: float
    previous: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None


class BWAResponse(BaseModel):
    """BWA-Report (Betriebswirtschaftliche Auswertung)."""
    period_start: date
    period_end: date
    rows: list[BWARow]


# ======= USt Schemas =======

class UStByRate(BaseModel):
    """USt-Daten nach Steuersatz."""
    rate: float
    output_vat: float  # Umsatzsteuer (aus Ausgangsrechnungen)
    input_vat: float   # Vorsteuer (aus Eingangsrechnungen)
    balance: float     # output_vat - input_vat


class UStResponse(BaseModel):
    """USt-Voranmeldung."""
    period_start: date
    period_end: date
    total_output_vat: float
    total_input_vat: float
    total_balance: float
    by_rate: list[UStByRate]


# ======= Open Items Schemas =======

class OpenItemResponse(BaseModel):
    """Offener Posten mit Ampel-Status."""
    id: int
    direction: str
    invoice_number: Optional[str]
    invoice_date: date
    due_date: Optional[date]
    gross_amount: float
    counterparty: Optional[str]
    days_until_due: Optional[int]  # Negativ = überfällig
    status_color: str  # "green" | "yellow" | "red"


# ======= Stats Schemas =======

class StatsResponse(BaseModel):
    """Badge-Statistiken für Sidebar."""
    total: int
    open: int
    overdue: int
