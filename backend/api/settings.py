"""
VERA Office - Settings API
GET /api/settings — Systemeinstellungen für Frontend
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from backend.db.database import get_db
from backend.api.auth import get_current_user
from backend.models.user import User
from backend.models.settings import Settings
from backend.config import config

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


def _system_fallback_sections() -> List[SettingSection]:
    """
    Aggregiert Live-Systemdaten als Fallback-Einstellungen.
    Wird verwendet wenn die DB-Einstellungstabelle leer ist.
    Vorbild: /api/system/status Daten.
    """
    vera_url = f"https://{config.HOST}:{config.HTTPS_PORT}" if config.HTTPS_PORT else f"http://{config.HOST}:{config.PORT}"

    # LLM-Modell aus config/vera.yaml ermitteln
    llm_model = "llama (lokal)"
    try:
        import yaml
        if config.CONFIG_FILE.exists():
            with open(config.CONFIG_FILE, "r", encoding="utf-8") as f:
                yaml_cfg = yaml.safe_load(f) or {}
            llm_model = yaml_cfg.get("llm_model") or yaml_cfg.get("LLM_MODEL") or llm_model
    except Exception:
        pass

    storage_path = str(config.DOCUMENTS_DIR)

    return [
        SettingSection(
            key="system_version",
            label="System-Version",
            description="Aktuelle VERA Office Version",
            value=config.APP_VERSION,
        ),
        SettingSection(
            key="backend_status",
            label="Backend-Status",
            description="Betriebsstatus des Backends",
            value="running",
        ),
        SettingSection(
            key="debug_mode",
            label="Debug-Modus",
            description="Debug-Logging aktiviert",
            value="an" if config.DEBUG else "aus",
        ),
        SettingSection(
            key="vera_url",
            label="VERA-URL",
            description="Adresse des VERA Office Servers",
            value=vera_url,
        ),
        SettingSection(
            key="llm_model",
            label="LLM-Modell",
            description="Verwendetes Sprachmodell für KI-Funktionen",
            value=llm_model,
        ),
        SettingSection(
            key="storage_path",
            label="Speicherpfad",
            description="Ablageort für Dokumente",
            value=storage_path,
        ),
    ]


@router.get("/settings", response_model=SettingsResponse, tags=["Settings"])
async def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Gibt alle gespeicherten Systemeinstellungen zurück.
    Jede Einstellung enthält key, label, description und value.
    Leere DB → Fallback auf Live-Systemdaten (version, status, debug, url, llm, storage).
    """
    rows: List[Settings] = db.query(Settings).order_by(Settings.category, Settings.key).all()

    if rows:
        sections = [
            SettingSection(
                key=row.key,
                label=_LABEL_MAP.get(row.key, row.key.replace("_", " ").title()),
                description=row.description or "",
                value=str(row.value) if row.value is not None else "",
            )
            for row in rows
        ]
    else:
        # Keine DB-Einstellungen → Live-Systemdaten aggregieren
        sections = _system_fallback_sections()

    return SettingsResponse(sections=sections)
