"""
VERA Office - Zentrale Konfiguration
Lädt Einstellungen aus config/vera.yaml und Umgebungsvariablen
"""
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic_settings import BaseSettings
from loguru import logger


class Settings(BaseSettings):
    """Konfiguration für VERA Office Backend"""
    
    # Pfade
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    INBOX_DIR: Path = DATA_DIR / "inbox"
    DOCUMENTS_DIR: Path = DATA_DIR / "documents"
    EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
    CONFIG_FILE: Path = BASE_DIR / "config" / "vera.yaml"
    
    # Datenbank
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/vera.db"
    
    # FastAPI
    APP_NAME: str = "VERA Office"
    APP_VERSION: str = "1.0.0-alpha"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Auth (JWT)
    SECRET_KEY: str = "VERA-OFFICE-SECRET-CHANGE-IN-PRODUCTION-PLEASE"  # In Production via ENV setzen!
    DEVICE_ID: Optional[str] = None  # Eindeutige Geräte-ID (UUID)
    
    # OCR
    OCR_LANGUAGE: str = "de"  # Deutsch
    OCR_GPU: bool = False  # CPU-only für Mini-PC
    
    # Bildverarbeitung
    IMAGE_MAX_SIZE: int = 2048  # Maximale Bildgröße für Verarbeitung
    IMAGE_DPI: int = 300  # DPI für PDF-Generierung
    IMAGE_QUALITY: int = 85  # JPEG-Qualität nach Kompression
    
    # Hotfolder
    HOTFOLDER_ENABLED: bool = True
    HOTFOLDER_POLL_INTERVAL: int = 2  # Sekunden
    
    # Klassifikation
    CLASSIFICATION_THRESHOLD: float = 0.8  # Konfidenz-Schwelle für automatische Ablage
    
    # Telemetrie
    TELEMETRY_ENABLED: bool = True
    TELEMETRY_SERVER_URL: str = "https://telemetry.vera-office.de/api/v1"
    TELEMETRY_DEVICE_ID: Optional[str] = None
    TELEMETRY_HEARTBEAT_INTERVAL: int = 30
    TELEMETRY_BATCH_SIZE: int = 50
    TELEMETRY_OFFLINE_BUFFER_MAX: int = 1000
    
    # Diagnostics
    DIAGNOSTICS_ENABLED: bool = True
    DIAGNOSTICS_CHECK_INTERVAL: int = 60
    DIAGNOSTICS_OCR_FAIL_THRESHOLD: int = 3
    DIAGNOSTICS_CONFIDENCE_WARNING_THRESHOLD: float = 0.5
    DIAGNOSTICS_DISK_WARNING_PERCENT: int = 90
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


def load_config() -> Settings:
    """
    Lädt Konfiguration aus yaml-Datei (falls vorhanden) und überschreibt mit Umgebungsvariablen
    """
    settings = Settings()
    
    # Erstelle Verzeichnisse falls nicht vorhanden
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.INBOX_DIR.mkdir(parents=True, exist_ok=True)
    settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    settings.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Lade YAML-Konfiguration (falls vorhanden)
    if settings.CONFIG_FILE.exists():
        try:
            with open(settings.CONFIG_FILE, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # Flache Keys
                    for key, value in yaml_config.items():
                        if hasattr(settings, key.upper()):
                            setattr(settings, key.upper(), value)
                    
                    # Nested: telemetry
                    if 'telemetry' in yaml_config and isinstance(yaml_config['telemetry'], dict):
                        for key, value in yaml_config['telemetry'].items():
                            attr_name = f"TELEMETRY_{key.upper()}"
                            if hasattr(settings, attr_name):
                                setattr(settings, attr_name, value)
                    
                    # Nested: diagnostics
                    if 'diagnostics' in yaml_config and isinstance(yaml_config['diagnostics'], dict):
                        for key, value in yaml_config['diagnostics'].items():
                            attr_name = f"DIAGNOSTICS_{key.upper()}"
                            if hasattr(settings, attr_name):
                                setattr(settings, attr_name, value)
            
            logger.info(f"Konfiguration geladen: {settings.CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"Fehler beim Laden der YAML-Konfiguration: {e}")
    else:
        logger.info(f"Keine YAML-Konfiguration gefunden, nutze Standardwerte")
    
    return settings


# Globale Config-Instanz
config = load_config()
