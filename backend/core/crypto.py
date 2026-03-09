"""
VERA Office Cryptographic License System
- RSA 4096-bit for signing
- AES-256-GCM for encryption
- Hardware-Binding via Device Fingerprint
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import json
import base64
import hashlib
import platform
import uuid
from pathlib import Path
from typing import Optional
from loguru import logger


def get_device_fingerprint() -> str:
    """
    Generate hardware-based device fingerprint.
    License is bound to THIS device only.
    """
    components = [
        platform.node(),           # Hostname
        str(uuid.getnode()),       # MAC Address
        platform.machine(),        # CPU Architecture
        platform.processor(),      # Processor
    ]
    
    # Optional: Disk Serial (Windows only)
    try:
        import subprocess
        result = subprocess.run(
            ['wmic', 'diskdrive', 'get', 'serialnumber'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Clean up the output
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            if len(lines) > 1:  # Skip header
                components.append(lines[1])
    except Exception as e:
        logger.debug(f"Could not read disk serial: {e}")
    
    raw = "|".join(components)
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()
    
    logger.debug(f"Device fingerprint components: {len(components)}")
    return fingerprint


def generate_rsa_keypair() -> tuple:
    """
    Generate RSA 4096-bit key pair.
    Returns: (private_key, public_key) as cryptography objects
    """
    logger.info("Generating RSA 4096-bit key pair...")
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )
    public_key = private_key.public_key()
    
    logger.info("RSA key pair generated successfully")
    return private_key, public_key


def save_private_key(private_key, path: Path, password: Optional[bytes] = None) -> None:
    """Save RSA private key to PEM file (optionally encrypted)"""
    encryption = serialization.NoEncryption()
    if password:
        encryption = serialization.BestAvailableEncryption(password)
    
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    logger.info(f"Private key saved to {path}")


def save_public_key(public_key, path: Path) -> None:
    """Save RSA public key to PEM file"""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    logger.info(f"Public key saved to {path}")


def load_private_key(path: Path, password: Optional[bytes] = None):
    """Load RSA private key from PEM file"""
    pem_data = path.read_bytes()
    private_key = serialization.load_pem_private_key(
        pem_data,
        password=password
    )
    logger.info(f"Private key loaded from {path}")
    return private_key


def load_public_key(path: Path):
    """Load RSA public key from PEM file"""
    pem_data = path.read_bytes()
    public_key = serialization.load_pem_public_key(pem_data)
    logger.info(f"Public key loaded from {path}")
    return public_key


def sign_data(private_key, data: bytes) -> bytes:
    """
    Sign data with RSA private key using PSS padding.
    Returns: signature bytes
    """
    signature = private_key.sign(
        data,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature


def verify_signature(public_key, data: bytes, signature: bytes) -> bool:
    """
    Verify RSA signature.
    Returns: True if valid, False otherwise
    """
    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        logger.warning(f"Signature verification failed: {e}")
        return False


def encrypt_license(license_data: dict, device_fingerprint: str) -> str:
    """
    Encrypt license data with AES-256-GCM.
    Key is derived from device fingerprint + salt.
    Only the original device can decrypt!
    
    Returns: JSON string with encrypted data
    """
    # 1. Serialize license data
    payload = json.dumps(license_data, sort_keys=True).encode()
    
    # 2. Generate salt and derive AES key from device fingerprint
    salt = os.urandom(16)
    aes_key = hashlib.sha256(device_fingerprint.encode() + salt).digest()
    
    # 3. Encrypt with AES-256-GCM
    nonce = os.urandom(12)
    aesgcm = AESGCM(aes_key)
    encrypted = aesgcm.encrypt(nonce, payload, None)
    
    # 4. Package: salt + nonce + encrypted
    output = {
        "v": 2,  # Version
        "s": base64.b64encode(salt).decode(),
        "n": base64.b64encode(nonce).decode(),
        "d": base64.b64encode(encrypted).decode()
    }
    
    return json.dumps(output)


def decrypt_license(encrypted_data: str, device_fingerprint: str) -> dict:
    """
    Decrypt license data with AES-256-GCM.
    Key is derived from device fingerprint + salt.
    
    Returns: Decrypted license data dict
    Raises: Exception if decryption fails (wrong device or tampering)
    """
    # 1. Parse encrypted package
    package = json.loads(encrypted_data)
    
    if package.get("v") != 2:
        raise ValueError("Unsupported license format version")
    
    salt = base64.b64decode(package["s"])
    nonce = base64.b64decode(package["n"])
    encrypted = base64.b64decode(package["d"])
    
    # 2. Derive AES key from device fingerprint
    aes_key = hashlib.sha256(device_fingerprint.encode() + salt).digest()
    
    # 3. Decrypt
    aesgcm = AESGCM(aes_key)
    try:
        decrypted = aesgcm.decrypt(nonce, encrypted, None)
    except Exception as e:
        raise ValueError(f"Decryption failed - license not valid for this device: {e}")
    
    # 4. Parse license data
    license_data = json.loads(decrypted)
    
    return license_data
