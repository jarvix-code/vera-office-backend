"""
VERA Office - Lizenz-Check beim Start (Ed25519 only)
Konsolidiert auf modules/license.py (Ed25519).
"""
from pathlib import Path
from loguru import logger


def check_license_on_startup(data_dir: Path) -> bool:
    """
    Prüft Lizenz beim Start via Ed25519 LicenseStore.
    
    Evaluierungs-Modus erlaubt: Kein Kill-Switch.
    """
    from backend.modules.license import LicenseStore
    
    # Public Key laden (shipped mit jeder VERA-Instanz)
    backend_dir = Path(__file__).parent.parent
    public_key_path = backend_dir / "config" / "vera_license.pub"
    
    if not public_key_path.exists():
        logger.error(f"Public Key fehlt: {public_key_path}")
        logger.warning(" VERA Office läuft im Evaluierungs-Modus (ohne Lizenz-Validierung)")
        return True
    
    public_key_pem = public_key_path.read_text()
    
    # LicenseStore initialisieren
    licenses_db = data_dir / "licenses.json"
    store = LicenseStore(licenses_db, public_key_pem)
    licenses = store.all_licenses()
    
    if not licenses:
        logger.warning("Keine Lizenz gefunden (data/licenses.json)")
        logger.info(" VERA Office läuft im Evaluierungs-Modus")
        return True
    
    # Prüfe ob mindestens eine Lizenz gültig ist
    valid_count = 0
    for module_name, status in licenses.items():
        if status == "active":
            valid_count += 1
            logger.success(f" Lizenz OK: {module_name}")
        elif status == "expired":
            logger.warning(f" Lizenz abgelaufen: {module_name}")
        else:
            logger.warning(f" Lizenz ungültig: {module_name}")
    
    logger.info(f"Lizenzen geladen: {valid_count}/{len(licenses)} gültig")
    return True  # Start immer erlauben
