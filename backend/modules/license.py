# v1.0: [MODULE-SYSTEM] Ed25519 Lizenzvalidierung
"""
Offline-fähige Modul-Lizenzierung mit Ed25519-Signaturen.

Lizenzschlüssel-Format (benutzer-sichtbar):
    VERA-ERP-eyJt-b2Qi-OiJl-cnAi-LC...-SIGBASE64
    
Aufbau: VERA-{MODUL}-{base64url_payload.base64url_signatur}
Chunks sind nur optische Formatierung (werden beim Parsing entfernt).

Payload (JSON):
    {"mod": "erp", "exp": null, "iss": "vera"}
    - mod: Modul-Name (muss mit required_license matchen)
    - exp: Ablaufdatum (ISO 8601) oder null für unbefristet
    - iss: Issuer (immer "vera")

Validierung:
    1. Regex-Match auf VERA-{MODULE}-{body}
    2. Body entchunken → payload_b64.sig_b64
    3. Base64url-Decode → payload_bytes + sig_bytes
    4. Ed25519 verify(sig_bytes, payload_bytes)
    5. Ablaufdatum prüfen
    
Persistierung:
    data/licenses.json: {"module_name": "VERA-ERP-..."}
"""

import re
import json
import base64
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Tuple
from loguru import logger

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey
    )
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("cryptography library not available - licensing disabled")
    CRYPTO_AVAILABLE = False


class LicenseStore:
    """
    Persistiert und validiert Modul-Lizenzschlüssel.
    
    Lizenz-Datenbank: JSON-Datei {module_name: license_key}
    Bei jedem is_licensed() wird der Schlüssel NEU validiert (inkl. Ablaufdatum).
    """
    
    def __init__(self, db_path: Path, public_key_pem: str):
        """
        Args:
            db_path: Pfad zu licenses.json
            public_key_pem: PEM-encoded Ed25519 Public Key
        """
        self.db_path = db_path
        self.public_key_pem = public_key_pem
        self._licenses: dict[str, str] = {}
        
        if not CRYPTO_AVAILABLE:
            logger.error("LicenseStore initialisiert aber cryptography fehlt!")
            return
        
        # Public Key laden
        try:
            self.public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Public Key laden fehlgeschlagen: {e}")
            self.public_key = None
        
        # Bestehende Lizenzen laden
        self._load()
    
    def _load(self):
        """Lädt Lizenzen aus JSON-Datei."""
        if not self.db_path.exists():
            logger.info(f"Keine Lizenz-DB gefunden: {self.db_path}")
            return
        
        try:
            with open(self.db_path, 'r') as f:
                self._licenses = json.load(f)
            logger.info(f"Lizenzen geladen: {list(self._licenses.keys())}")
        except Exception as e:
            logger.warning(f"Lizenz-DB beschädigt: {e} - starte leer")
            self._licenses = {}
    
    def _save(self):
        """Speichert Lizenzen in JSON-Datei."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump(self._licenses, f, indent=2)
            logger.info(f"Lizenzen gespeichert: {list(self._licenses.keys())}")
        except Exception as e:
            logger.error(f"Speichern fehlgeschlagen: {e}")
    
    def activate(self, key: str) -> Tuple[bool, str]:
        """
        Aktiviert eine Lizenz (validiert + speichert).
        
        Args:
            key: Lizenzschlüssel (z.B. "VERA-ERP-eyJt...")
        
        Returns:
            (erfolg, nachricht)
        """
        if not CRYPTO_AVAILABLE:
            return False, "Kryptographie-Library fehlt"
        
        if not self.public_key:
            return False, "Public Key nicht geladen"
        
        # Validiere Schlüssel
        valid, module_name, error_msg = self._validate_key(key)
        if not valid:
            return False, error_msg
        
        # Speichern
        self._licenses[module_name] = key
        self._save()
        
        logger.success(f"Lizenz aktiviert: {module_name}")
        return True, f"Modul '{module_name}' freigeschaltet"
    
    def deactivate(self, module: str) -> bool:
        """
        Entfernt eine Lizenz.
        
        Args:
            module: Modul-Name (z.B. "erp")
        
        Returns:
            True wenn entfernt, False wenn nicht vorhanden
        """
        if module in self._licenses:
            del self._licenses[module]
            self._save()
            logger.info(f"Lizenz deaktiviert: {module}")
            return True
        return False
    
    def is_licensed(self, module: str) -> bool:
        """
        Prüft ob ein Modul lizenziert ist.
        WICHTIG: Re-validiert bei JEDEM Aufruf (inkl. Ablaufdatum)!
        
        Args:
            module: Modul-Name (z.B. "erp")
        
        Returns:
            True wenn Lizenz gültig, False sonst
        """
        if not CRYPTO_AVAILABLE or not self.public_key:
            logger.debug(f"is_licensed({module}): CRYPTO_AVAILABLE={CRYPTO_AVAILABLE}, public_key={self.public_key is not None}")
            return False
        
        key = self._licenses.get(module)
        if not key:
            logger.debug(f"is_licensed({module}): Kein Key gefunden in {list(self._licenses.keys())}")
            return False
        
        valid, _, msg = self._validate_key(key)
        logger.debug(f"is_licensed({module}): valid={valid}, msg={msg}, key={key[:30]}...")
        return valid
    
    def get_status(self, module: str) -> str:
        """
        Gibt Lizenzstatus zurück.
        
        Returns:
            "active" | "expired" | "none"
        """
        if module not in self._licenses:
            return "none"
        
        key = self._licenses[module]
        valid, _, error = self._validate_key(key)
        
        if valid:
            return "active"
        elif "abgelaufen" in error:
            return "expired"
        else:
            return "none"
    
    def all_licenses(self) -> dict[str, str]:
        """
        Gibt alle Lizenzen mit Status zurück.
        
        Returns:
            {module_name: status}
        """
        return {
            module: self.get_status(module)
            for module in self._licenses
        }
    
    def _validate_key(self, key: str) -> Tuple[bool, Optional[str], str]:
        """
        Validiert einen Lizenzschlüssel.
        
        Returns:
            (valid, module_name, error_message)
        """
        # Regex: VERA-{MODULE}-{BASE64}
        match = re.match(r'^VERA-([A-Z]+)-(.+)$', key, re.IGNORECASE)
        if not match:
            return False, None, "Ungültiges Format (erwartet: VERA-{MODUL}-{KEY})"
        
        module_name = match.group(1).lower()
        body = match.group(2)
        
        # KEIN Entchunken mehr (base64url nutzt '-' selbst!)
        # body bleibt unverändert
        
        # Splitten am Punkt: payload_b64.sig_b64
        if '.' not in body:
            return False, module_name, "Ungültiges Format (Punkt fehlt)"
        
        parts = body.rsplit('.', 1)  # Splitte beim LETZTEN Punkt
        if len(parts) != 2:
            return False, module_name, "Ungültiges Format (kein Delimiter)"
        
        payload_b64, sig_b64 = parts
        
        # Base64url-Decode (Padding korrigieren)
        try:
            # Padding hinzufügen (mod 4)
            payload_padding = '=' * ((4 - len(payload_b64) % 4) % 4)
            sig_padding = '=' * ((4 - len(sig_b64) % 4) % 4)
            
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + payload_padding)
            sig_bytes = base64.urlsafe_b64decode(sig_b64 + sig_padding)
        except Exception as e:
            return False, module_name, f"Base64-Decode fehlgeschlagen: {e}"
        
        # Payload parsen
        try:
            payload = json.loads(payload_bytes)
        except Exception as e:
            return False, module_name, f"JSON-Parse fehlgeschlagen: {e}"
        
        # Payload-Struktur prüfen
        if payload.get('iss') != 'vera':
            return False, module_name, "Ungültiger Issuer"
        
        if payload.get('mod') != module_name:
            return False, module_name, f"Modul-Mismatch (erwartet: {module_name}, gefunden: {payload.get('mod')})"
        
        # Ablaufdatum prüfen
        exp = payload.get('exp')
        if exp:
            try:
                exp_date = date.fromisoformat(exp)
                if exp_date < date.today():
                    return False, module_name, f"Lizenz abgelaufen am {exp}"
            except Exception as e:
                return False, module_name, f"Ungültiges Ablaufdatum: {e}"
        
        # Ed25519-Signatur verifizieren
        try:
            self.public_key.verify(sig_bytes, payload_bytes)
        except Exception as e:
            return False, module_name, f"Signatur ungültig: {e}"
        
        return True, module_name, "OK"


def generate_keypair() -> Tuple[str, str]:
    """
    Generiert ein Ed25519-Schlüsselpaar.
    ACHTUNG: Nur für Admin/Build-Server!
    
    Returns:
        (private_key_pem, public_key_pem)
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library nicht verfügbar")
    
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return priv_pem, pub_pem


def create_license_key(
    private_key_pem: str,
    module: str,
    expiry: Optional[date] = None
) -> str:
    """
    Erstellt einen Lizenzschlüssel.
    ACHTUNG: Nur für Admin/Build-Server!
    
    Args:
        private_key_pem: PEM-encoded Ed25519 Private Key
        module: Modul-Name (z.B. "erp")
        expiry: Ablaufdatum (None = unbefristet)
    
    Returns:
        Lizenzschlüssel (z.B. "VERA-ERP-eyJt...")
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography library nicht verfügbar")
    
    # Private Key laden
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None
    )
    
    # Payload erstellen
    payload = {
        "mod": module.lower(),
        "exp": expiry.isoformat() if expiry else None,
        "iss": "vera"
    }
    
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    # Signieren
    signature = private_key.sign(payload_bytes)
    
    # Base64url-Encode (ohne Padding für kompaktere Keys)
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')
    sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')
    
    # Kombinieren mit Punkt als Delimiter
    body = f"{payload_b64}.{sig_b64}"
    
    # KEIN Chunking mehr (base64url nutzt selbst '-' als Zeichen!)
    # Chunking würde beim Entchunken auch base64url-'-' entfernen
    
    # Finaler Schlüssel
    key = f"VERA-{module.upper()}-{body}"
    
    return key
