# v1.0: [MODULE-SYSTEM] Keygen CLI — Ed25519 Schlüsselpaar-Generierung
"""
CLI-Tool zum Erstellen des Ed25519-Schlüsselpaars für VERA Modul-Lizenzen.

Verwendung:
    python -m backend.modules.keygen
    
Erstellt:
    - backend/config/vera_license.key (PRIVATE — NUR für Boris/Build-Server!)
    - backend/config/vera_license.pub (PUBLIC — shipped mit jeder VERA-Instanz)

Wichtig:
    - Nur EINMAL ausführen (bricht ab wenn Dateien existieren)
    - Private Key NIEMALS committen oder teilen!
    - Public Key wird in jeder VERA-Instanz ausgeliefert
    
Admin-Tool:
    Lizenzschlüssel erzeugen:
    
    from backend.modules.license import create_license_key
    from datetime import date
    
    priv_pem = open("backend/config/vera_license.key").read()
    key = create_license_key(priv_pem, module="erp", expiry=date(2027, 1, 1))
    print(key)
"""

from pathlib import Path
from loguru import logger

from .license import generate_keypair


def main():
    """
    Hauptfunktion: Generiert Ed25519-Schlüsselpaar.
    """
    logger.info("🔑 VERA Lizenz-Schlüsselpaar-Generator")
    
    # Pfade
    backend_dir = Path(__file__).parent.parent
    config_dir = backend_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    private_key_path = config_dir / "vera_license.key"
    public_key_path = config_dir / "vera_license.pub"
    
    # Prüfe ob Schlüssel bereits existieren
    if private_key_path.exists() or public_key_path.exists():
        logger.error("❌ Schlüsselpaar existiert bereits!")
        logger.info(f"   Private: {private_key_path}")
        logger.info(f"   Public:  {public_key_path}")
        logger.warning("Wenn du ein NEUES Schlüsselpaar erstellen willst, lösche die bestehenden Dateien zuerst.")
        logger.warning("⚠️  ACHTUNG: Alle bestehenden Lizenzschlüssel werden ungültig!")
        return
    
    # Schlüsselpaar generieren
    logger.info("Generiere Ed25519-Schlüsselpaar...")
    private_pem, public_pem = generate_keypair()
    
    # Speichern
    private_key_path.write_text(private_pem)
    public_key_path.write_text(public_pem)
    
    logger.success(f"✅ Private Key: {private_key_path}")
    logger.success(f"✅ Public Key:  {public_key_path}")
    
    logger.warning("")
    logger.warning("⚠️  WICHTIG:")
    logger.warning("   - Private Key NIEMALS committen oder teilen!")
    logger.warning("   - Private Key ist NUR für Boris/Build-Server")
    logger.warning("   - Public Key wird mit jeder VERA-Instanz ausgeliefert")
    logger.warning("")
    logger.info("Lizenzschlüssel erstellen:")
    logger.info("   from backend.modules.license import create_license_key")
    logger.info("   from datetime import date")
    logger.info(f"   priv_pem = open('{private_key_path}').read()")
    logger.info("   key = create_license_key(priv_pem, module='erp', expiry=date(2027, 1, 1))")
    logger.info("   print(key)")


if __name__ == "__main__":
    main()
