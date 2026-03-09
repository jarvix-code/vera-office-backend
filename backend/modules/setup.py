# v1.0: [MODULE-SYSTEM] Bootstrap — setup_modules()
"""
setup_modules(app): Initialisiert das gesamte Modul-System.

Wird von main.py aufgerufen (nach init_db, vor app.run).

Workflow:
    1. Public Key aus config/vera_license.pub laden
    2. LicenseStore erstellen (data/licenses.json)
    3. ModuleRegistry erstellen
    4. Meta-API mounten (/api/modules, /api/modules/license)
    5. Built-in Module registrieren (ERP, QM)
    6. Modul-Routes mounten
    7. Middleware hinzufügen
    8. Registry zurückgeben

Pfade (relativ zu backend/):
    - Public Key: config/vera_license.pub
    - Lizenz-DB: ../data/licenses.json
    
Fehlerfall:
    - Public Key fehlt → FileNotFoundError
    - Built-in Module fehlen → ImportError (wird geloggt, nicht kritisch)
"""

from pathlib import Path
from fastapi import FastAPI
from loguru import logger

from .license import LicenseStore
from .registry import ModuleRegistry
from .middleware import ModuleLicenseMiddleware


def setup_modules(app: FastAPI) -> ModuleRegistry:
    """
    Initialisiert das Modul-System.
    
    Args:
        app: FastAPI-Instanz
    
    Returns:
        ModuleRegistry (für spätere Nutzung)
    
    Raises:
        FileNotFoundError: Wenn Public Key fehlt
    """
    logger.info("🔧 Modul-System wird initialisiert...")
    
    # Pfade (relativ zu backend/)
    backend_dir = Path(__file__).parent.parent
    public_key_path = backend_dir / "config" / "vera_license.pub"
    license_db_path = backend_dir.parent / "data" / "licenses.json"
    
    # 1. Public Key laden
    if not public_key_path.exists():
        raise FileNotFoundError(
            f"Public Key nicht gefunden: {public_key_path}\n"
            "Bitte 'python -m backend.modules.keygen' ausführen um Schlüsselpaar zu erstellen."
        )
    
    public_key_pem = public_key_path.read_text()
    logger.info(f"Public Key geladen: {public_key_path}")
    
    # 2. LicenseStore erstellen
    license_store = LicenseStore(license_db_path, public_key_pem)
    logger.info(f"LicenseStore initialisiert: {license_db_path}")
    
    # 3. ModuleRegistry erstellen
    registry = ModuleRegistry(license_store)
    
    # 4. Meta-API mounten
    meta_router = registry.create_api_router()
    app.include_router(meta_router)
    logger.info("Meta-API gemountet: /api/modules, /api/modules/license")
    
    # 5. Built-in Module registrieren
    # Versuche ERP + QM zu laden (wenn vorhanden)
    # Fehler werden geloggt aber nicht kritisch (Module können später hinzugefügt werden)
    
    # ERP-Modul registrieren
    try:
        from backend.modules.erp import erp_module
        registry.register(erp_module)
        logger.success("✅ ERP-Modul registriert")
    except ImportError as e:
        logger.warning(f"⚠️ ERP-Modul nicht verfügbar: {e}")
    
    # QM-Modul registrieren
    try:
        from backend.modules.qm import qm_module
        registry.register(qm_module)
        logger.success("✅ QM-Modul registriert")
    except ImportError as e:
        logger.warning(f"⚠️ QM-Modul nicht verfügbar: {e}")
    
    logger.info(f"Module registriert: {len(registry.all_modules())}")
    
    # 6. Modul-Routes mounten
    registry.mount_all(app)
    
    # 7. Middleware hinzufügen
    app.add_middleware(ModuleLicenseMiddleware, registry=registry)
    logger.success("✅ Modul-System initialisiert")
    
    return registry
