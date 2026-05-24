# v1.0: [ERP] Finanzdaten-Extraktion aus VERA-Dokumenten
"""
Extrahiert Finanzdaten aus bereits klassifizierten VERA-Dokumenten.

Workflow:
    1. VERA klassifiziert Dokument als "Rechnung" (via docagent)
    2. extractor.extract_from_document(doc) wird aufgerufen
    3. Richtungserkennung (Keywords in Klassifikation)
    4. Betragsberechnung (auto netto↔brutto)
    5. Datumsparser (ISO + deutsches DD.MM.YYYY)
    6. -> FinancialRecord (zur DB-Speicherung bereit)

Wichtig:
    - ERP extrahiert NUR — klassifiziert nicht selbst!
    - Richtungserkennung via Keywords (nicht perfect, aber gut genug)
    - Auto-Fälligkeitsdatum: +30 Tage bei Eingangsrechnungen
"""

import re
from datetime import date, timedelta
from typing import Optional, Dict, Any
from loguru import logger


def extract_from_document(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extrahiert Finanzdaten aus einem VERA-Dokument.
    
    Args:
        doc: VERA-Dokument-Dict mit:
            - classification: str (z.B. "Eingangsrechnung")
            - extracted_data: dict mit Metadaten (amount, date, etc.)
            - ocr_text: str (optional, für Fallback-Extraktion)
    
    Returns:
        Dict mit FinancialRecord-Daten oder None wenn kein Finanz-Dokument
    """
    # Richtungserkennung
    direction = _detect_direction(doc.get('classification', ''))
    if not direction:
        logger.debug(f"Dokument {doc.get('id')} ist kein Finanzdokument")
        return None
    
    # Extrahierte Daten aus VERA
    extracted = doc.get('extracted_data', {})
    
    # Beträge extrahieren
    net = _parse_amount(extracted.get('net_amount'))
    gross = _parse_amount(extracted.get('gross_amount') or extracted.get('total_amount'))
    vat_rate = float(extracted.get('vat_rate', 19.0))
    
    # Auto-Berechnung: Netto ↔ Brutto
    if net and not gross:
        vat_amount = net * vat_rate / 100
        gross = net + vat_amount
    elif gross and not net:
        net = gross / (1 + vat_rate / 100)
        vat_amount = gross - net
    elif net and gross:
        vat_amount = gross - net
    else:
        # Kein Betrag -> Fallback: Suche in OCR-Text
        gross = _extract_amount_from_text(doc.get('ocr_text', ''))
        if not gross:
            logger.warning(f"Dokument {doc.get('id')}: Kein Betrag gefunden")
            return None
        net = gross / (1 + vat_rate / 100)
        vat_amount = gross - net
    
    # Daten extrahieren
    invoice_date = _parse_date(extracted.get('invoice_date') or extracted.get('date'))
    due_date = _parse_date(extracted.get('due_date'))
    
    # Auto-Fälligkeitsdatum: +30 Tage bei Eingangsrechnungen
    if not due_date and direction == 'incoming' and invoice_date:
        due_date = invoice_date + timedelta(days=30)
    
    # Record zusammenstellen
    record = {
        'document_id': doc.get('id'),
        'direction': direction,
        'invoice_number': extracted.get('invoice_number'),
        'invoice_date': invoice_date or date.today(),  # Fallback: heute
        'due_date': due_date,
        'net_amount': round(net, 2),
        'vat_rate': vat_rate,
        'vat_amount': round(vat_amount, 2),
        'gross_amount': round(gross, 2),
        'counterparty': extracted.get('counterparty') or extracted.get('sender') or 'Unbekannt',
        'category': doc.get('classification'),
        'payment_status': 'open',
    }
    
    logger.info(
        f"Finanzdaten extrahiert: {direction} | {record['counterparty']} | "
        f"{record['gross_amount']}€ (brutto)"
    )
    
    return record


def _detect_direction(classification: str) -> Optional[str]:
    """
    Erkennt Geldfluss-Richtung aus Klassifikation.
    
    Args:
        classification: Klassifikations-String (z.B. "Eingangsrechnung")
    
    Returns:
        "incoming" | "outgoing" | None
    """
    if not classification:
        return None
    
    c = classification.lower()
    
    # Eingangsrechnung = Kosten (incoming)
    if any(kw in c for kw in ['eingang', 'incoming', 'lieferant', 'kosten', 'expense']):
        return 'incoming'
    
    # Ausgangsrechnung = Umsatz (outgoing)
    if any(kw in c for kw in ['ausgang', 'outgoing', 'kunde', 'umsatz', 'revenue']):
        return 'outgoing'
    
    # Generischer "Rechnung"-Match -> Eingang (konservativer Default)
    if 'rechnung' in c or 'invoice' in c:
        return 'incoming'
    
    return None


def _parse_amount(val: Any) -> Optional[float]:
    """
    Parst Beträge mit deutschen/englischen Zahlenformaten.
    
    Unterstützt:
        - 1.234,56 (deutsch)
        - 1234,56
        - 1234.56
        - "1.234,56 €"
    
    Args:
        val: Betrag (str, float, int)
    
    Returns:
        Float oder None
    """
    if val is None:
        return None
    
    if isinstance(val, (int, float)):
        return float(val)
    
    if not isinstance(val, str):
        return None
    
    # Entferne Währungssymbole und Leerzeichen
    val = val.replace('€', '').replace('EUR', '').strip()
    
    # Deutsches Format: 1.234,56 -> 1234.56
    if ',' in val and '.' in val:
        # Punkt = Tausender, Komma = Dezimal
        val = val.replace('.', '').replace(',', '.')
    elif ',' in val:
        # Nur Komma -> Dezimal
        val = val.replace(',', '.')
    
    try:
        return float(val)
    except ValueError:
        return None


def _parse_date(val: Any) -> Optional[date]:
    """
    Parst Datum (ISO oder deutsches Format).
    
    Unterstützt:
        - 2026-02-15 (ISO)
        - 15.02.2026 (deutsch)
        - date-Objekt
    
    Args:
        val: Datum (str, date)
    
    Returns:
        date oder None
    """
    if val is None:
        return None
    
    if isinstance(val, date):
        return val
    
    if not isinstance(val, str):
        return None
    
    # ISO-Format: YYYY-MM-DD
    try:
        return date.fromisoformat(val)
    except ValueError:
        pass
    
    # Deutsches Format: DD.MM.YYYY
    match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', val)
    if match:
        day, month, year = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass
    
    logger.warning(f"Datum nicht parsbar: {val}")
    return None


def _extract_amount_from_text(text: str) -> Optional[float]:
    """
    Extrahiert Betrag aus OCR-Text (Fallback).
    Sucht nach Keywords wie "Summe", "Gesamt", "Total" + Betrag.
    
    Args:
        text: OCR-Text
    
    Returns:
        Float oder None
    """
    if not text:
        return None
    
    # IRS Form 1120: taxable income (Line 30) has priority over "Total assets" in header
    irs_pattern = r'taxable\s+income.{0,200}?(\d{4,})'
    irs_match = re.search(irs_pattern, text.lower())
    if irs_match:
        return _parse_amount(irs_match.group(1))
    
    # Pattern: "Summe: 1.234,56 EUR" oder "Gesamt 1234,56€"
    pattern = r'(?:summe|gesamt|total|betrag)[:\s]*([\d.,]+)\s*€?'
    match = re.search(pattern, text.lower())
    
    if match:
        return _parse_amount(match.group(1))
    
    return None
