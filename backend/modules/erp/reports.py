# v1.0: [ERP] Reports — CSV & DATEV Export
"""
Export-Funktionen für ERP-Daten.

Formate:
- CSV: Semikolon-getrennt, deutsche Feldnamen, UTF-8
- DATEV: Buchungsstapel v700, cp1252, SKR03

Wichtig:
- DATEV = cp1252 Encoding (NICHT UTF-8!)
- DATEV Belegdatum = TTMM (nur Tag+Monat, kein Jahr!)
- DATEV Umsatz = Bruttobetrag
- DATEV BU-Schlüssel steuert Automatik-USt
"""

import hashlib
from io import StringIO
from datetime import date
from typing import List
from sqlalchemy.orm import Session

from .models import FinancialRecord, Direction


# ======= CSV Export =======

def export_csv(db: Session, start: date, end: date) -> str:
    """
    Exportiert Records als CSV (Semikolon-getrennt, UTF-8).
    
    Args:
        db: SQLAlchemy Session
        start: Perioden-Start
        end: Perioden-Ende
    
    Returns:
        CSV-String
    """
    records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= start,
        FinancialRecord.invoice_date <= end
    ).order_by(FinancialRecord.invoice_date).all()
    
    output = StringIO()
    
    # Header (deutsche Feldnamen)
    output.write(
        'Datum;Rechnungsnr;Richtung;Geschäftspartner;Kategorie;'
        'Netto;MwSt%;MwSt-Betrag;Brutto;Status;Fälligkeitsdatum\n'
    )
    
    # Datenzeilen
    for r in records:
        direction_label = 'Ausgang' if r.direction == Direction.OUTGOING else 'Eingang'
        status_label = {
            'open': 'Offen',
            'paid': 'Bezahlt',
            'overdue': 'Überfällig'
        }.get(r.payment_status.value if hasattr(r.payment_status, 'value') else r.payment_status, r.payment_status)
        
        output.write(
            f'{r.invoice_date.isoformat()};'
            f'{r.invoice_number or ""};'
            f'{direction_label};'
            f'{r.counterparty or ""};'
            f'{r.category or ""};'
            f'{_format_amount(r.net_amount)};'
            f'{_format_amount(r.vat_rate)};'
            f'{_format_amount(r.vat_amount)};'
            f'{_format_amount(r.gross_amount)};'
            f'{status_label};'
            f'{r.due_date.isoformat() if r.due_date else ""}\n'
        )
    
    return output.getvalue()


def _format_amount(val: float) -> str:
    """Formatiert Beträge im deutschen Format (Komma als Dezimaltrenner)."""
    return f'{val:.2f}'.replace('.', ',')


# ======= DATEV Export =======

# SKR03 Konten-Mapping (vereinfacht)
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
REVENUE_ACCOUNT = 8400  # Erlöse 19% USt


def export_datev(
    db: Session,
    start: date,
    end: date,
    berater_nr: int,
    mandanten_nr: int
) -> bytes:
    """
    Exportiert Records als DATEV Buchungsstapel v700 (cp1252).
    
    Args:
        db: SQLAlchemy Session
        start: Perioden-Start (bestimmt Wirtschaftsjahr)
        end: Perioden-Ende
        berater_nr: DATEV Berater-Nummer
        mandanten_nr: DATEV Mandanten-Nummer
    
    Returns:
        CSV-Bytes (cp1252 encoded)
    """
    records = db.query(FinancialRecord).filter(
        FinancialRecord.invoice_date >= start,
        FinancialRecord.invoice_date <= end
    ).order_by(FinancialRecord.invoice_date).all()
    
    output = StringIO()
    
    # Header-Zeile 1: Formatdeskriptor
    wj_beginn = start.strftime('%Y%m%d')  # Wirtschaftsjahr-Beginn
    output.write(
        f'"EXTF";"700";"21";"Buchungsstapel";"7";"";"";"";'
        f'{berater_nr};{mandanten_nr};{wj_beginn};4;"EUR"\n'
    )
    
    # Header-Zeile 2: Spaltennamen (20 Felder)
    output.write(
        '"Umsatz";"Soll/Haben";"WKZ";"Kurs";"Basis-Umsatz";"WKZ Basis-Umsatz";'
        '"Konto";"Gegenkonto";"BU-Schl\u00FCssel";"Belegdatum";"Belegfeld 1";'
        '"Belegfeld 2";"Skonto";"Buchungstext";"Postensperre";"Diverse Adressnummer";'
        '"Gesch\u00E4ftsbereich";"Sachverhalt";"Zinssperre";"Beleglink"\n'
    )
    
    # Datenzeilen
    for r in records:
        # Konto und Gegenkonto
        if r.direction == Direction.INCOMING:
            # Eingangsrechnung: Aufwandskonto (Soll) ← Kreditor (Haben)
            konto = _get_expense_account(r.category)
            gegenkonto = _get_kreditor(r.counterparty)
        else:
            # Ausgangsrechnung: Debitor (Soll) -> Erlöskonto (Haben)
            konto = _get_debitor(r.counterparty)
            gegenkonto = REVENUE_ACCOUNT
        
        # BU-Schlüssel (Automatik-USt)
        bu_schluessel = _get_bu_schluessel(r.vat_rate)
        
        # Belegdatum: TTMM (Tag+Monat, KEIN Jahr!)
        belegdatum = r.invoice_date.strftime('%d%m')
        
        # Umsatz = Bruttobetrag
        umsatz = _format_amount(r.gross_amount)
        
        # Buchungstext: Geschäftspartner (max 60 Zeichen)
        buchungstext = (r.counterparty or 'Unbekannt')[:60]
        
        # Soll/Haben
        soll_haben = 'S'  # Default: Soll
        
        # Zeile schreiben
        output.write(
            f'"{umsatz}";"'
            f'{soll_haben}";"EUR";"";"";"";"'
            f'{konto}";"'
            f'{gegenkonto}";"'
            f'{bu_schluessel}";"'
            f'{belegdatum}";"'
            f'{r.invoice_number or ""}";"";"";"'
            f'{buchungstext}";"";"";"";"";"";""'
            f'\n'
        )
    
    # Zu cp1252 konvertieren
    csv_str = output.getvalue()
    return csv_str.encode('cp1252', errors='replace')


def _get_expense_account(category: str) -> int:
    """Gibt SKR03-Aufwandskonto für Kategorie zurück."""
    return CATEGORY_TO_ACCOUNT.get(category, DEFAULT_EXPENSE_ACCOUNT)


def _get_kreditor(name: str) -> int:
    """
    Generiert Kreditor-Kontonummer (70000er Bereich).
    WICHTIG: Hash-basiert -> INSTABIL zwischen Python-Runs!
    TODO: Persistierung in DB für Konsistenz.
    """
    if not name:
        return 70000
    
    # MD5-Hash (stabil, nicht security-relevant)
    hash_val = int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16)
    return 70000 + (hash_val % 9999)


def _get_debitor(name: str) -> int:
    """
    Generiert Debitor-Kontonummer (10000er Bereich).
    WICHTIG: Hash-basiert -> INSTABIL zwischen Python-Runs!
    TODO: Persistierung in DB für Konsistenz.
    """
    if not name:
        return 10000
    
    hash_val = int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16)
    return 10000 + (hash_val % 9999)


def _get_bu_schluessel(vat_rate: float) -> int:
    """
    Gibt DATEV BU-Schlüssel für MwSt-Satz zurück.
    
    BU-Schlüssel steuert Automatik-USt:
    - 3 = 19% USt
    - 2 = 7% USt
    - 0 = steuerfrei
    """
    if vat_rate >= 19:
        return 3
    elif vat_rate >= 7:
        return 2
    else:
        return 0
