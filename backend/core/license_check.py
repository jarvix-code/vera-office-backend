"""
VERA Office - Lizenz-Check beim Start (Ed25519 konsolidiert)
Prüft ob eine gültige Lizenz existiert. Kein Kill-Switch.
Konsolidiert: Alle Lizenzprüfungen verwenden jetzt Ed25519 (modules/license.py).
"""
from pathlib import Path
from loguru import logger


def check_license_on_startup(data_dir: Path) -> bool:
    """
    Prüft Lizenz beim Start. Gibt True zurück wenn gültig.
    
    Drei Modi:
    1. Keine Lizenz-Datei -> Evaluierungs-Modus (erlaubt)
    2. Ed25519-Lizenz in licenses.json -> Validieren
    3. Alte license.key Datei -> Ignorieren (deprecated)
    """
    licenses_file = data_dir / "licenses.json"
    
    if not licenses_file.exists():
        logger.warning("Keine Lizenz-Datei gefunden (data/licenses.json)")
        logger.info("   VERA Office läuft im Evaluierungs-Modus")
        return True  # Erlaubt Start ohne Lizenz
    
    # Ed25519-Lizenzen werden vom ModuleRegistry geprüft
    # Hier nur prüfen ob die Datei lesbar ist
    try:
        import json
        data = json.loads(licenses_file.read_text(encoding='utf-8'))
        license_count = len(data)
        logger.info(f"Lizenzen geladen: {license_count} Modul(e) lizenziert")
        return True
    except Exception as e:
        logger.error(f"Lizenz-Datei beschädigt: {e}")
        return True  # Start trotzdem erlauben, Module prüfen selbst
