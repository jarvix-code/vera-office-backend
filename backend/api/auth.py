"""
VERA Office Auth API
JWT-basierte Authentifizierung mit Rollen-System + Conversational Auth
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import uuid

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from backend.db.database import get_db
from backend.models.user import User, ROLES
from backend.config import config
from backend.core.ai.auth_conversation import AuthConversation


# JWT Settings
SECRET_KEY = config.SECRET_KEY if hasattr(config, "SECRET_KEY") else "VERA-OFFICE-SECRET-CHANGE-IN-PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================
# Schemas
# ============================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_admin: bool
    permissions: list
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "viewer"

class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class ChatAuthRequest(BaseModel):
    """Request for conversational authentication"""
    message: str
    session_id: Optional[str] = None

class ChatAuthResponse(BaseModel):
    """Response for conversational authentication"""
    message: str  # VERA's response
    suggestions: List[str] = []  # Quick-reply suggestions
    auth_state: str  # Current auth state (greeting, username, password, authenticated, locked)
    authenticated: bool  # True if user is authenticated
    token: Optional[str] = None  # JWT token (only if authenticated)
    user_info: Optional[dict] = None  # User info (only if authenticated)
    session_id: str  # Session ID for next request


# ============================================================
# In-Memory Session Store
# ============================================================

# Store for auth conversation sessions (in-memory for MVP)
# In production: move to Redis or DB table
_auth_sessions: Dict[str, AuthConversation] = {}

def get_auth_session(session_id: str, db: Session) -> AuthConversation:
    """Get or create auth conversation session."""
    if session_id not in _auth_sessions:
        _auth_sessions[session_id] = AuthConversation(db_session=db)
    else:
        # Update db session (might have changed between requests)
        _auth_sessions[session_id].db = db
    return _auth_sessions[session_id]

def cleanup_auth_session(session_id: str):
    """Remove auth session from memory (after successful login or timeout)."""
    if session_id in _auth_sessions:
        del _auth_sessions[session_id]


# ============================================================
# Helper Functions
# ============================================================

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def _user_to_response(user: User) -> dict:
    """Konvertiert User-Model zu Response-Dict mit Rollen-Info."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_admin": user.role == "admin",
        "is_active": user.is_active,
        "permissions": user.permissions,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ============================================================
# Dependencies
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    
    return user


def require_permission(permission: str):
    """Dependency-Factory für Rollen-basierte Berechtigung."""
    async def checker(current_user: User = Depends(get_current_user)):
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Keine Berechtigung: {permission}"
            )
        return current_user
    return checker


# ============================================================
# Endpoints
# ============================================================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    
    user.last_login = datetime.now()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    
    logger.info(f"User logged in: {user.username} (role: {user.role})")
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=_user_to_response(user)
    )

@router.post("/chat", response_model=ChatAuthResponse)
async def chat_auth(request: ChatAuthRequest, db: Session = Depends(get_db)):
    """
    Conversational authentication endpoint.
    
    Flow:
    1. GREETING: "Mit wem habe ich heute das Vergnügen?"
    2. USERNAME: User gibt Namen ein
    3. PASSWORD: "Gib mir das Passwort um dich zu bestätigen!"
    4. AUTHENTICATED: Success → JWT Token
    
    Security:
    - Rate-Limiting: max 3 password attempts
    - Lockout: 5 minutes after 3 failed attempts
    
    Args:
        request: ChatAuthRequest with message and optional session_id
        db: Database session
    
    Returns:
        ChatAuthResponse with VERA's response, auth state, and token (if authenticated)
    """
    try:
        # Get or create session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get or create auth conversation
        conversation = get_auth_session(session_id, db)
        
        # Process user input
        result = conversation.process_input(request.message, db)
        
        # Cleanup session if authenticated (user doesn't need it anymore)
        if result["authenticated"]:
            cleanup_auth_session(session_id)
            logger.info(f"User authenticated via chat: {result.get('user_info', {}).get('username', 'unknown')}")
        
        # Return response
        return ChatAuthResponse(
            message=result["message"],
            suggestions=result["suggestions"],
            auth_state=result["auth_state"],
            authenticated=result["authenticated"],
            token=result.get("token"),
            user_info=result.get("user_info"),
            session_id=session_id
        )
    
    except Exception as e:
        logger.error(f"Error in chat auth endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during authentication")

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    logger.info(f"User logged out: {current_user.username}")
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return _user_to_response(current_user)

@router.post("/create-user")
async def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    """Erstellt neuen User (Onboarding oder Admin)."""
    existing = db.query(User).filter(User.username == request.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if request.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Ungültige Rolle. Erlaubt: {list(ROLES.keys())}")
    
    user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        is_active=True,
        is_admin=(request.role == "admin")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.success(f"User created: {user.username} (role: {user.role})")
    return _user_to_response(user)

@router.get("/roles")
async def get_roles(current_user: User = Depends(get_current_user)):
    """Gibt alle verfügbaren Rollen zurück."""
    return {"roles": ROLES}

# ============================================================
# Admin: User-Verwaltung
# ============================================================

@router.get("/users")
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users"))
):
    """Listet alle User auf (nur Admin)."""
    users = db.query(User).all()
    return {"users": [_user_to_response(u) for u in users]}

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users"))
):
    """Aktualisiert einen User (nur Admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.role is not None:
        if request.role not in ROLES:
            raise HTTPException(status_code=400, detail=f"Ungültige Rolle: {request.role}")
        user.role = request.role
        user.is_admin = (request.role == "admin")
    
    if request.email is not None:
        user.email = request.email
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.is_active is not None:
        user.is_active = request.is_active
    if request.password is not None:
        user.password_hash = hash_password(request.password)
    
    db.commit()
    db.refresh(user)
    logger.info(f"User updated: {user.username}")
    return _user_to_response(user)

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users"))
):
    """Deaktiviert einen User (soft delete, nur Admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Eigenen Account kann man nicht löschen")
    
    user.is_active = False
    db.commit()
    logger.info(f"User deactivated: {user.username}")
    return {"message": f"User {user.username} deaktiviert"}


# ============================================================
# Setup Router — Ersteinrichtung (Name + Master-PW + PIN)
# ============================================================

setup_router = APIRouter(prefix="/api/setup", tags=["setup"])

# PIN_SESSION_EXPIRE_HOURS: Wie lange ein PIN-Token gültig ist
PIN_SESSION_EXPIRE_HOURS = 8


class SetupInitRequest(BaseModel):
    name: str
    master_password: str  # 8-stellig
    pin: str              # 6-stellig


class VerifyPinRequest(BaseModel):
    pin: str
    name: Optional[str] = None  # Optionaler Anzeigename ("Wer bist du?")


class VerifyMasterRequest(BaseModel):
    master_password: str


class ModuleUnlockRequest(BaseModel):
    module: str
    master_password: str


@setup_router.get("/status")
async def setup_status(db: Session = Depends(get_db)):
    """
    Gibt zurück ob VERA bereits eingerichtet ist.
    Wird beim App-Start geprüft — wenn nicht initialisiert → Onboarding.
    """
    user = db.query(User).filter(User.pin_hash.isnot(None)).first()
    if user:
        modules = []
        try:
            modules = json.loads(user.modules_unlocked or '[]')
        except Exception:
            modules = []
        return {
            "initialized": True,
            "name": user.name or user.username,
            "modules_unlocked": modules
        }
    return {"initialized": False, "name": None, "modules_unlocked": []}


@setup_router.post("/init")
async def setup_init(request: SetupInitRequest, db: Session = Depends(get_db)):
    """
    Ersteinrichtung: Name + Master-PW + PIN festlegen.
    Kann nur aufgerufen werden wenn noch kein User mit PIN existiert.
    """
    # Prüfe ob schon eingerichtet
    existing = db.query(User).filter(User.pin_hash.isnot(None)).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="VERA ist bereits eingerichtet. Bitte Master-Passwort nutzen."
        )

    # Validierung
    if len(request.master_password) < 8:
        raise HTTPException(status_code=400, detail="Master-Passwort muss mindestens 8 Zeichen haben")
    if len(request.pin) < 4:
        raise HTTPException(status_code=400, detail="PIN muss mindestens 4 Zeichen haben")
    if len(request.name.strip()) < 1:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    # User erstellen oder bestehenden ersten User upgraden
    user = db.query(User).first()

    if user:
        # Bestehenden User mit neuen Feldern ergänzen
        user.name = request.name.strip()
        user.master_pw_hash = hash_password(request.master_password)
        user.pin_hash = hash_password(request.pin)
        user.modules_unlocked = '[]'
    else:
        # Neuen User erstellen
        user = User(
            username=request.name.strip().lower().replace(" ", "_"),
            password_hash=hash_password(request.master_password),
            name=request.name.strip(),
            master_pw_hash=hash_password(request.master_password),
            pin_hash=hash_password(request.pin),
            modules_unlocked='[]',
            role="admin",
            is_active=True,
            is_admin=True
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # Trial-Lizenz erstellen wenn noch keine existiert
    try:
        from pathlib import Path
        from backend.core.license import LicenseService
        data_dir = Path("data")
        lic_service = LicenseService(data_dir)
        if not lic_service.is_active():
            lic_service.create_trial(customer_name=request.name.strip())
            logger.info(f"Trial-Lizenz erstellt für: {request.name}")
    except Exception as e:
        logger.warning(f"Trial-Lizenz konnte nicht erstellt werden: {e}")

    # Onboarding als abgeschlossen markieren
    try:
        from backend.models.settings import OnboardingState
        onboarding = db.query(OnboardingState).first()
        if not onboarding:
            onboarding = OnboardingState()
            db.add(onboarding)
        onboarding.completed = True
        onboarding.current_step = 99
        db.commit()
    except Exception as e:
        logger.warning(f"Onboarding-Status konnte nicht gesetzt werden: {e}")

    logger.success(f"VERA Setup abgeschlossen: {user.name}")
    return {
        "success": True,
        "message": f"Willkommen, {user.name}! VERA ist jetzt eingerichtet.",
        "name": user.name
    }


# ============================================================
# Neue Endpoints im bestehenden Auth-Router
# ============================================================

@router.post("/verify-pin")
async def verify_pin(request: VerifyPinRequest, db: Session = Depends(get_db)):
    """
    PIN prüfen für Modul-Zugriff.
    Gibt PIN-Session-Token zurück (gültig für 8 Stunden).
    Token enthält freigeschaltete Module (modules_unlocked).
    """
    # Try user with pin_hash first; fall back to admin user
    user = db.query(User).filter(User.pin_hash.isnot(None)).first()
    if not user:
        user = db.query(User).filter(User.is_admin.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="VERA ist noch nicht eingerichtet. Bitte Einrichtung durchführen."
        )

    # Verify PIN: bcrypt if pin_hash set, else check Settings.user_pin (plaintext)
    pin_valid = False
    if user.pin_hash:
        pin_valid = verify_password(request.pin, user.pin_hash)
    else:
        from backend.models.settings import Settings as SettingsModel
        setting = db.query(SettingsModel).filter(SettingsModel.key == "user_pin").first()
        if setting:
            pin_valid = (request.pin == setting.value)

    if not pin_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsche PIN. Bitte erneut versuchen."
        )

    # Freigeschaltete Module laden
    # Admin-User bekommen automatisch alle verfuegbaren Module
    ALL_MODULES = ['erp', 'qm', 'datev']
    if getattr(user, 'is_admin', False):
        unlocked_modules = ALL_MODULES
    else:
        try:
            unlocked_modules = json.loads(user.modules_unlocked or '[]')
        except Exception:
            unlocked_modules = []

    display_name = user.name or getattr(user, 'full_name', None) or user.username

    # PIN-Session-Token erstellen (mit Modulen)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "type": "pin_session",
            "name": display_name,
            "modules": unlocked_modules
        },
        expires_delta=timedelta(hours=PIN_SESSION_EXPIRE_HOURS)
    )

    logger.info(f"PIN-Session erstellt für: {display_name} — Module: {unlocked_modules}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_hours": PIN_SESSION_EXPIRE_HOURS,
        "name": display_name,
        "modules": unlocked_modules
    }


@router.post("/verify-master")
async def verify_master(request: VerifyMasterRequest, db: Session = Depends(get_db)):
    """
    Master-Passwort prüfen (für Modulkauf/Freischaltung).
    Gibt Bestätigung zurück (kein langer Token, nur kurzfristige Bestätigung).
    """
    user = db.query(User).filter(User.master_pw_hash.isnot(None)).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="VERA ist noch nicht eingerichtet."
        )

    if not user.master_pw_hash or not verify_password(request.master_password, user.master_pw_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsches Master-Passwort."
        )

    # Kurzes Master-Token (5 Minuten) für Modul-Freischaltung
    token = create_access_token(
        data={
            "sub": str(user.id),
            "type": "master_session",
            "name": user.name or user.username
        },
        expires_delta=timedelta(minutes=5)
    )

    logger.info(f"Master-Passwort verifiziert für: {user.name or user.username}")
    return {"verified": True, "token": token, "name": user.name or user.username}


@router.post("/modules/unlock")
async def unlock_module(request: ModuleUnlockRequest, db: Session = Depends(get_db)):
    """
    Modul für Benutzer freischalten (benötigt Master-Passwort).
    Fügt das Modul zur modules_unlocked-Liste des Users hinzu.
    """
    user = db.query(User).filter(User.master_pw_hash.isnot(None)).first()
    if not user:
        raise HTTPException(status_code=404, detail="VERA ist noch nicht eingerichtet.")

    if not user.master_pw_hash or not verify_password(request.master_password, user.master_pw_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsches Master-Passwort."
        )

    # Modul zur Liste hinzufügen
    try:
        unlocked = json.loads(user.modules_unlocked or '[]')
    except Exception:
        unlocked = []

    module_name = request.module.lower()
    if module_name not in unlocked:
        unlocked.append(module_name)
        user.modules_unlocked = json.dumps(unlocked)
        db.commit()
        logger.success(f"Modul '{module_name}' freigeschaltet für: {user.name or user.username}")

    return {
        "success": True,
        "message": f"Modul '{module_name}' wurde freigeschaltet.",
        "modules_unlocked": unlocked
    }
