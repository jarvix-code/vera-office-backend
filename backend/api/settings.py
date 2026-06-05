"""
VERA Office - Settings API
GET /api/settings — Systemeinstellungen für Frontend
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from backend.db.database import get_db
from backend.models.settings import Settings

router = APIRouter()


class SettingSection(BaseModel):
    """Einzelne Einstellung für das Frontend"""
    key: str
    label: str
    description: str
    value: str


class SettingsResponse(BaseModel):
    """Response für GET /api/settings"""
    sections: List[SettingSection]


# Lesbarer Label pro Key (Fallback: key selbst)
_LABEL_MAP: dict[str, str] = {
    "company_name": "Unternehmensname",
    "company_type": "Unternehmenstyp",
    "industry": "Branche",
    "employee_count": "Mitarbeiterzahl",
    "hotfolder_path": "Eingangsordner",
    "storage_path": "Speicherpfad",
    "auto_file": "Automatische Ablage",
    "confidence_threshold": "Konfidenz-Schwellenwert",
    "language": "Sprache",
    "timezone": "Zeitzone",
    "email_enabled": "E-Mail aktiviert",
    "email_host": "E-Mail Server",
    "email_port": "E-Mail Port",
    "network_folder": "Netzwerkordner",
    "ocr_engine": "OCR Engine",
    "llm_provider": "LLM Anbieter",
    "llm_model": "LLM Modell",
    "debug_mode": "Debug-Modus",
}


@router.get("/settings", response_model=SettingsResponse, tags=["Settings"])
async def get_settings(db: Session = Depends(get_db)):
    """
    Gibt alle gespeicherten Systemeinstellungen zurück.
    Jede Einstellung enthält key, label, description und value.
    Leere DB → leere sections-Liste (Frontend zeigt EmptyState).
    """
    rows: List[Settings] = db.query(Settings).order_by(Settings.category, Settings.key).all()

    sections = [
        SettingSection(
            key=row.key,
            label=_LABEL_MAP.get(row.key, row.key.replace("_", " ").title()),
            description=row.description or "",
            value=str(row.value) if row.value is not None else "",
        )
        for row in rows
    ]

    return SettingsResponse(sections=sections)
