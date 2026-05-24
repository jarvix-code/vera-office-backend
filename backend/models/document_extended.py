"""
VERA Office - Extended Document Model with Deadline Tracking
Migration adds deadline/payment tracking columns
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.db.database import Base


# THIS IS THE MIGRATION - ADD THESE COLUMNS TO documents TABLE:
"""
ALTER TABLE documents ADD COLUMN payment_due_date DATETIME;
ALTER TABLE documents ADD COLUMN contract_end_date DATETIME;
ALTER TABLE documents ADD COLUMN deadline_type VARCHAR(64);
ALTER TABLE documents ADD COLUMN deadline_status VARCHAR(32) DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN keywords TEXT;  -- JSON array
ALTER TABLE documents ADD COLUMN deadline_completed_at DATETIME;
ALTER TABLE documents ADD COLUMN deadline_completed_by INTEGER;  -- user_id

CREATE INDEX idx_payment_due ON documents(payment_due_date) WHERE deadline_status = 'pending';
CREATE INDEX idx_contract_end ON documents(contract_end_date) WHERE deadline_status = 'pending';
"""


class DocumentExtended(Base):
    """
    Extended Document Model (for new installations)
    Existing installations: use migration script
    """
    __tablename__ = "documents"
    
    # ... (existing columns from document.py)
    
    # === NEW: Deadline Tracking ===
    
    # Zahlungsziel (für Rechnungen)
    payment_due_date = Column(DateTime, nullable=True, index=True)
    
    # Vertragsende (für Verträge)
    contract_end_date = Column(DateTime, nullable=True, index=True)
    
    # Art der Frist
    deadline_type = Column(
        String(64), 
        nullable=True
    )  # "payment", "contract", "retention", "review"
    
    # Frist-Status
    deadline_status = Column(
        String(32), 
        nullable=True, 
        default="pending",
        index=True
    )  # "pending", "completed", "overdue", "ignored"
    
    # Schlagworte (für Dashboard-Suche)
    keywords = Column(Text, nullable=True)  # JSON: ["Steuer", "2024", "Praxis"]
    
    # Abhak-Tracking
    deadline_completed_at = Column(DateTime, nullable=True)
    deadline_completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # === DASHBOARD QUERY EXAMPLE ===
    """
    # Zeige überfällige Zahlungen
    SELECT * FROM documents 
    WHERE payment_due_date < DATE('now')
    AND deadline_status = 'pending'
    ORDER BY payment_due_date ASC;
    
    # Zeige Fristen in nächsten 7 Tagen
    SELECT * FROM documents
    WHERE (
        payment_due_date BETWEEN DATE('now') AND DATE('now', '+7 days')
        OR contract_end_date BETWEEN DATE('now') AND DATE('now', '+7 days')
    )
    AND deadline_status = 'pending';
    
    # Abhaken
    UPDATE documents 
    SET deadline_status = 'completed',
        deadline_completed_at = CURRENT_TIMESTAMP,
        deadline_completed_by = :user_id
    WHERE id = :doc_id;
    """
