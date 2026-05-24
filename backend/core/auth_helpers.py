"""
VERA Office - Authentication Helper Functions
Shared crypto/JWT utilities to avoid circular imports between auth.py and auth_conversation.py
"""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
import jwt

# JWT Settings (imported from config in auth.py, duplicated here for independence)
SECRET_KEY = "VERA-OFFICE-SECRET-CHANGE-IN-PRODUCTION"  # Will be overridden by config
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, secret_key: str = SECRET_KEY) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (e.g. {"sub": username, "role": role})
        expires_delta: Token expiration time (default: 24 hours)
        secret_key: JWT secret key (default: global SECRET_KEY)
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str = SECRET_KEY) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
        secret_key: JWT secret key (default: global SECRET_KEY)
    
    Returns:
        Decoded payload dict, or None if invalid/expired
    """
    try:
        return jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def set_secret_key(key: str):
    """Set global SECRET_KEY (called from config on app startup)."""
    global SECRET_KEY
    SECRET_KEY = key
