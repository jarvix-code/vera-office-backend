# v1.0: [ERP] SQLAlchemy Models
"""
FinancialRecord: Tabelle für Finanzdaten (Rechnungen, Ausgaben, Einnahmen).

Wird von extractor.py automatisch aus klassifizierten VERA-Dokumenten befüllt.
Dashboard/BWA/USt nutzen diese Tabelle für Aggregationen.
"""

from datetime import date, datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Direction(PyEnum):
    """Richtung des Geldflusses."""
    INCOMING = "incoming"  # Eingangsrechnung (Kosten/Ausgaben)
    OUTGOING = "outgoing"  # Ausgangsrechnung (Umsatz/Einnahmen)


class PaymentStatus(PyEnum):
    """Zahlungsstatus."""
    OPEN = "open"          # Unbezahlt
    PAID = "paid"          # Bezahlt
    OVERDUE = "overdue"    # Überfällig


class FinancialRecord(Base):
    """
    Finanzdaten-Record (Rechnung).
    
    Wichtig:
    - Beträge in EUR (Float)
    - Netto, Brutto, MwSt separat gespeichert
    - direction: incoming = Kosten, outgoing = Umsatz
    - Auto-generiert aus VERA-Dokumenten via extractor.py
    """
    __tablename__ = "erp_financial_records"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Verknüpfung zu VERA-Dokument (nullable, weil manuell erstellte Records möglich)
    document_id = Column(String(255), nullable=True, index=True)
    
    # Richtung (Eingang/Ausgang)
    direction = Column(Enum(Direction), nullable=False, index=True)
    
    # Rechnungsdaten
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=True)
    
    # Beträge (EUR)
    net_amount = Column(Float, nullable=False)      # Nettobetrag
    vat_rate = Column(Float, nullable=False, default=19.0)  # MwSt-Satz (%)
    vat_amount = Column(Float, nullable=False)      # MwSt-Betrag
    gross_amount = Column(Float, nullable=False)    # Bruttobetrag
    
    # Geschäftspartner
    counterparty = Column(String(255), nullable=True, index=True)  # Lieferant/Kunde
    
    # Kategorie (aus VERA-Klassifikation)
    category = Column(String(100), nullable=True, index=True)
    
    # Zahlungsstatus
    payment_status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.OPEN, index=True)
    payment_date = Column(Date, nullable=True)
    
    # Notizen
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return (
            f"<FinancialRecord(id={self.id}, "
            f"direction={self.direction.value}, "
            f"gross={self.gross_amount}, "
            f"counterparty={self.counterparty})>"
        )
