"""
VERA Office - Path Resolution Utility
Unterstützt Deployment-Szenarien: Development, Installed, Portable.
"""
import os
from pathlib import Path


def get_vera_home() -> Path:
    """
    Gibt VERA_HOME Verzeichnis zurück.
    
    Priorität:
    1. VERA_HOME Environment Variable (von Installer gesetzt)
    2. Fallback: 4 Ebenen nach oben von diesem File (__file__)
    
    Struktur:
        VERA_HOME/
         backend/
            core/
               paths.py (dieses File)
         frontend/
         data/
         config/
         models/
    """
    env_home = os.getenv("VERA_HOME")
    if env_home:
        return Path(env_home)
    
    # Fallback: __file__ -> core -> backend -> VERA_HOME
    return Path(__file__).parent.parent.parent


# Globale Konstanten für häufig genutzte Pfade
VERA_HOME = get_vera_home()
DATA_DIR = VERA_HOME / "data"
CONFIG_DIR = VERA_HOME / "config"
MODELS_DIR = VERA_HOME / "models"
FRONTEND_DIST_DIR = VERA_HOME / "frontend" / "dist"
