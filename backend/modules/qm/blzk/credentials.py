"""
BLZK Credentials Management
Encrypted storage for BLZK portal credentials.
"""
import json
import base64
import os
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from loguru import logger


CREDENTIALS_DIR = Path("data/credentials")
CREDENTIALS_FILE = CREDENTIALS_DIR / "blzk_credentials.enc"
KEY_FILE = CREDENTIALS_DIR / ".blzk_key"


def _get_or_create_key() -> bytes:
    """Gets or creates the encryption key."""
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    # Restrict permissions (Windows: best effort)
    try:
        import stat
        KEY_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass
    
    logger.info("BLZK encryption key created")
    return key


def _get_fernet() -> Fernet:
    """Returns Fernet instance with stored key."""
    return Fernet(_get_or_create_key())


def save_credentials(username: str, password: str) -> Dict[str, Any]:
    """
    Encrypts and saves BLZK credentials.
    
    Returns:
        Dict with success status
    """
    try:
        f = _get_fernet()
        data = json.dumps({
            "username": username,
            "password": password,
        }).encode()
        
        encrypted = f.encrypt(data)
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_bytes(encrypted)
        
        logger.info(f"BLZK credentials saved for user: {username}")
        return {"success": True, "username": username}
    except Exception as e:
        logger.error(f"Failed to save BLZK credentials: {e}")
        return {"success": False, "error": str(e)}


def load_credentials() -> Optional[Dict[str, str]]:
    """
    Loads and decrypts BLZK credentials.
    
    Returns:
        Dict with username/password or None if not found
    """
    if not CREDENTIALS_FILE.exists():
        return None
    
    try:
        f = _get_fernet()
        encrypted = CREDENTIALS_FILE.read_bytes()
        decrypted = f.decrypt(encrypted)
        data = json.loads(decrypted.decode())
        return data
    except Exception as e:
        logger.error(f"Failed to load BLZK credentials: {e}")
        return None


def has_credentials() -> bool:
    """Check if credentials are stored."""
    return CREDENTIALS_FILE.exists()


def delete_credentials() -> Dict[str, Any]:
    """Delete stored credentials."""
    try:
        if CREDENTIALS_FILE.exists():
            CREDENTIALS_FILE.unlink()
            logger.info("BLZK credentials deleted")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to delete BLZK credentials: {e}")
        return {"success": False, "error": str(e)}


def get_credentials_status() -> Dict[str, Any]:
    """Returns credential status (without exposing password)."""
    creds = load_credentials()
    if creds:
        return {
            "configured": True,
            "username": creds["username"],
            "has_password": bool(creds.get("password")),
        }
    return {
        "configured": False,
        "username": None,
        "has_password": False,
    }
