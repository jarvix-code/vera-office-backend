# v1.0: [ERP] Calculator — Dashboard, BWA, USt-Voranmeldung
"""
Aggregationen für ERP-Reports.

Funktionen:
- calculate_dashboard() → Revenue, Expenses, Profit, Monthly, Top Suppliers/Customers
- calculate_bwa() → BWA-Report (Netto-basiert, mit Periodenvergleich)
- calculate_ust() → USt-Voranmeldung (Output VAT - Input VAT)

Wichtig:
- Dashboard = Brutto-basiert (Cashflow-Sicht)
- BWA = Netto-basiert (steuerliche Sicht)
"""

from datetime import date, timedelta
from typing import List
from collections import defaultdict
from sqlalchemy.orm import Session

from .models import FinancialRecord, Direction
from .schemas import (
    DashboardResponse,
    MonthlyStats,
    CategoryBreakdown,
    TopCounterparty,
    PeriodComparison,
    BWAResponse,
    BWARow,
    UStResponse,
    UStByRate
)


# ======= Dashboard =======

def calculate_dashboard(
    db: Session,
    start: date,
    end: date
) -> DashboardResponse:
    """
    Berechnet Dashboard-Daten (Brutto-basiert).
    
    Args:
        db: SQLAlchemy Session
        start: Perioden-Start
        end: Perioden-Ende
    
    Returns:
        DashboardResponse
    """
    # Alle Records im Zeitraum
    records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= start,
        FinancialRecord.invoice_date <= end
    ).all()
    
    # Totale
    total_revenue = sum(r.gross_amount for r in records if r.direction == Direction.OUTGOING)
    total_expenses = sum(r.gross_amount for r in records if r.direction == Direction.INCOMING)
    total_profit = total_revenue - total_expenses
    
    # Monatliche Aggregation
    monthly_data = defaultdict(lambda: {'revenue': 0.0, 'expenses': 0.0})
    for r in records:
        month_key = r.invoice_date.strftime('%Y-%m')
        if r.direction == Direction.OUTGOING:
            monthly_data[month_key]['revenue'] += r.gross_amount
        else:
            monthly_data[month_key]['expenses'] += r.gross_amount
    
    monthly = [
        MonthlyStats(
            month=month,
            revenue=data['revenue'],
            expenses=data['expenses'],
            profit=data['revenue'] - data['expenses']
        )
        for month, data in sorted(monthly_data.items())
    ]
    
    # Kategorie-Breakdown (nur Ausgaben)
    category_data = defaultdict(float)
    for r in records:
        if r.direction == Direction.INCOMING and r.category:
            category_data[r.category] += r.gross_amount
    
    categories = [
        CategoryBreakdown(category=cat, amount=amt)
        for cat, amt in sorted(category_data.items(), key=lambda x: -x[1])
    ]
    
    # Top 10 Suppliers
    supplier_data = defaultdict(float)
    for r in records:
        if r.direction == Direction.INCOMING and r.counterparty:
            supplier_data[r.counterparty] += r.gross_amount
    
    top_suppliers = [
        TopCounterparty(name=name, amount=amt)
        for name, amt in sorted(supplier_data.items(), key=lambda x: -x[1])[:10]
    ]
    
    # Top 10 Customers
    customer_data = defaultdict(float)
    for r in records:
        if r.direction == Direction.OUTGOING and r.counterparty:
            customer_data[r.counterparty] += r.gross_amount
    
    top_customers = [
        TopCounterparty(name=name, amount=amt)
        for name, amt in sorted(customer_data.items(), key=lambda x: -x[1])[:10]
    ]
    
    # Periodenvergleich (Vorperiode = gleiche Länge vor Start)
    period_length = (end - start).days
    prev_start = start - timedelta(days=period_length + 1)
    prev_end = start - timedelta(days=1)
    
    prev_records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= prev_start,
        FinancialRecord.invoice_date <= prev_end
    ).all()
    
    prev_revenue = sum(r.gross_amount for r in prev_records if r.direction == Direction.OUTGOING)
    prev_expenses = sum(r.gross_amount for r in prev_records if r.direction == Direction.INCOMING)
    prev_profit = prev_revenue - prev_expenses
    
    delta = total_profit - prev_profit
    delta_pct = (delta / prev_profit * 100) if prev_profit != 0 else 0.0
    
    comparison = PeriodComparison(
        current=total_profit,
        previous=prev_profit,
        delta=delta,
        delta_pct=round(delta_pct, 2)
    )
    
    return DashboardResponse(
        total_revenue=round(total_revenue, 2),
        total_expenses=round(total_expenses, 2),
        total_profit=round(total_profit, 2),
        monthly=monthly,
        categories=categories,
        top_suppliers=top_suppliers,
        top_customers=top_customers,
        comparison=comparison
    )


# ======= BWA =======

# SKR03 Kategorie-Mapping (vereinfacht)
CATEGORY_TO_ACCOUNT = {
    'Material': 3400,
    'Büro': 4930,
    'Miete': 4210,
    'Versicherung': 4360,
    'Telefon': 4920,
    'Werbung': 4600,
    'Fahrzeug': 4500,
    'Reparatur': 4800,
}
DEFAULT_EXPENSE_ACCOUNT = 4900  # Sonstige Aufwendungen


def calculate_bwa(
    db: Session,
    start: date,
    end: date
) -> BWAResponse:
    """
    Berechnet BWA (Betriebswirtschaftliche Auswertung).
    WICHTIG: Netto-basiert!
    
    Args:
        db: SQLAlchemy Session
        start: Perioden-Start
        end: Perioden-Ende
    
    Returns:
        BWAResponse
    """
    # Aktuelle Periode
    records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= start,
        FinancialRecord.invoice_date <= end
    ).all()
    
    # Vorperiode (gleiche Länge)
    period_length = (end - start).days
    prev_start = start - timedelta(days=period_length + 1)
    prev_end = start - timedelta(days=1)
    
    prev_records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= prev_start,
        FinancialRecord.invoice_date <= prev_end
    ).all()
    
    # Umsatzerlöse (Netto)
    revenue = sum(r.net_amount for r in records if r.direction == Direction.OUTGOING)
    prev_revenue = sum(r.net_amount for r in prev_records if r.direction == Direction.OUTGOING)
    
    # Aufwand nach Kategorie (Netto)
    expense_by_category = defaultdict(float)
    for r in records:
        if r.direction == Direction.INCOMING:
            category = r.category or 'Sonstige'
            expense_by_category[category] += r.net_amount
    
    prev_expense_by_category = defaultdict(float)
    for r in prev_records:
        if r.direction == Direction.INCOMING:
            category = r.category or 'Sonstige'
            prev_expense_by_category[category] += r.net_amount
    
    total_expense = sum(expense_by_category.values())
    prev_total_expense = sum(prev_expense_by_category.values())
    
    # Betriebsergebnis
    operating_result = revenue - total_expense
    prev_operating_result = prev_revenue - prev_total_expense
    
    # Rows zusammenstellen
    rows = []
    
    # Umsatzerlöse
    rows.append(_bwa_row('Umsatzerlöse', revenue, prev_revenue))
    rows.append(_bwa_row('Gesamtleistung', revenue, prev_revenue))
    
    # Aufwandskategorien
    all_categories = set(expense_by_category.keys()) | set(prev_expense_by_category.keys())
    for category in sorted(all_categories):
        current = expense_by_category.get(category, 0.0)
        previous = prev_expense_by_category.get(category, 0.0)
        rows.append(_bwa_row(f'  {category}', current, previous))
    
    # Gesamtaufwand
    rows.append(_bwa_row('Gesamtaufwand', total_expense, prev_total_expense))
    
    # Betriebsergebnis
    rows.append(_bwa_row('Betriebsergebnis', operating_result, prev_operating_result))
    
    return BWAResponse(
        period_start=start,
        period_end=end,
        rows=rows
    )


def _bwa_row(label: str, current: float, previous: float) -> BWARow:
    """Helper: Erstellt eine BWA-Zeile mit Delta."""
    delta = current - previous
    delta_pct = (delta / previous * 100) if previous != 0 else 0.0
    
    return BWARow(
        label=label,
        current=round(current, 2),
        previous=round(previous, 2),
        delta=round(delta, 2),
        delta_pct=round(delta_pct, 2)
    )


# ======= USt-Voranmeldung =======

def calculate_ust(
    db: Session,
    start: date,
    end: date
) -> UStResponse:
    """
    Berechnet USt-Voranmeldung (Umsatzsteuer-Voranmeldung).
    
    Args:
        db: SQLAlchemy Session
        start: Perioden-Start
        end: Perioden-Ende
    
    Returns:
        UStResponse
    """
    records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= start,
        FinancialRecord.invoice_date <= end
    ).all()
    
    # Nach MwSt-Satz gruppieren
    vat_by_rate = defaultdict(lambda: {'output': 0.0, 'input': 0.0})
    
    for r in records:
        rate = r.vat_rate
        if r.direction == Direction.OUTGOING:
            vat_by_rate[rate]['output'] += r.vat_amount
        else:
            vat_by_rate[rate]['input'] += r.vat_amount
    
    # Totale
    total_output = sum(data['output'] for data in vat_by_rate.values())
    total_input = sum(data['input'] for data in vat_by_rate.values())
    total_balance = total_output - total_input
    
    # By-Rate Details
    by_rate = [
        UStByRate(
            rate=rate,
            output_vat=round(data['output'], 2),
            input_vat=round(data['input'], 2),
            balance=round(data['output'] - data['input'], 2)
        )
        for rate, data in sorted(vat_by_rate.items(), reverse=True)
    ]
    
    return UStResponse(
        period_start=start,
        period_end=end,
        total_output_vat=round(total_output, 2),
        total_input_vat=round(total_input, 2),
        total_balance=round(total_balance, 2),
        by_rate=by_rate
    )
