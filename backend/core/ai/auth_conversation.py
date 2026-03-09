"""
VERA Conversational Authentication
State machine for natural login conversation (chat-based auth instead of login form)

Inspired by Boris' vision:
    VERA: Mit wem habe ich heute das Vergnügen?
    User: Boris
    VERA: Gib mir das Passwort um dich zu bestätigen!
    User: [password]
    VERA: Danke, hallo Boris! Was liegt an?
"""
import re
import time
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.core.auth_helpers import verify_password, create_access_token

logger = logging.getLogger(__name__)


class AuthState(str, Enum):
    """Authentication conversation states"""
    GREETING = "greeting"
    USERNAME = "username"
    PASSWORD = "password"
    AUTHENTICATED = "authenticated"
    LOCKED = "locked"  # After too many failed attempts


class AuthConversation:
    """
    Manages conversational authentication flow.
    
    Flow:
    1. GREETING: "Mit wem habe ich heute das Vergnügen?"
    2. USERNAME: User gibt Namen ein
    3. PASSWORD: "Gib mir das Passwort um dich zu bestätigen!"
    4. AUTHENTICATED: Success → JWT Token
    
    Security:
    - Rate-Limiting: max 3 password attempts
    - Lockout: 5 minutes after 3 failed attempts
    - Password masking in Chat (frontend shows dots)
    """
    
    # Security settings
    MAX_PASSWORD_ATTEMPTS = 3
    LOCKOUT_DURATION_MINUTES = 5
    
    def __init__(self, session_data: Optional[Dict] = None, db_session: Optional[Session] = None):
        """
        Initialize authentication conversation.
        
        Args:
            session_data: Previously saved session data (for resuming)
            db_session: SQLAlchemy database session for user lookups
        """
        self.data = session_data or {}
        self.db = db_session
        self.current_state = AuthState(self.data.get("current_state", AuthState.GREETING))
        
        # Rate-limiting data
        self.failed_attempts = self.data.get("failed_attempts", 0)
        self.locked_until = self.data.get("locked_until", None)
        if self.locked_until:
            self.locked_until = datetime.fromisoformat(self.locked_until)
    
    def get_message(self) -> str:
        """Get current state message."""
        if self.current_state == AuthState.GREETING:
            return "Hallo! Mit wem habe ich heute das Vergnügen?"
        
        elif self.current_state == AuthState.USERNAME:
            # Validation failed or user not found
            error_msg = self.data.get("username_error", "")
            if error_msg:
                return f"{error_msg}\n\nWie heißt du?"
            return "Wie heißt du?"
        
        elif self.current_state == AuthState.PASSWORD:
            username = self.data.get("username", "du")
            attempts_left = self.MAX_PASSWORD_ATTEMPTS - self.failed_attempts
            
            if self.failed_attempts == 0:
                return f"Gib mir das Passwort um dich zu bestätigen, {username}!"
            else:
                return (
                    f"Passwort falsch, versuch's nochmal! "
                    f"({attempts_left} Versuch{'e' if attempts_left > 1 else ''} noch)"
                )
        
        elif self.current_state == AuthState.LOCKED:
            locked_until = self.locked_until or datetime.now()
            minutes_left = int((locked_until - datetime.now()).total_seconds() / 60)
            
            return (
                f"Zu viele Fehlversuche! Ich muss dich leider aussperren.\n\n"
                f"Versuch es in {minutes_left} Minute{'n' if minutes_left > 1 else ''} nochmal."
            )
        
        elif self.current_state == AuthState.AUTHENTICATED:
            username = self.data.get("username", "")
            return f"Danke, hallo {username}! Was liegt an?"
        
        return "Entschuldigung, da ist etwas schiefgelaufen."
    
    def get_suggestions(self) -> List[str]:
        """Get quick reply suggestions for current state."""
        if self.current_state == AuthState.AUTHENTICATED:
            return ["Dokument suchen", "Was fehlt?", "Letzte Dokumente"]
        
        # No suggestions for login flow (security: no hints for attackers)
        return []
    
    def process_input(self, user_input: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Process user input and advance state.
        
        Args:
            user_input: User's message
            db: SQLAlchemy database session (required for username/password validation)
        
        Returns:
            Dict with response message, suggestions, auth_state, token (if authenticated), and session data
        """
        user_input = user_input.strip()
        
        # Use provided db session or stored one
        if db:
            self.db = db
        
        # Check if locked
        if self.current_state == AuthState.LOCKED:
            if self._check_lockout_expired():
                # Lockout expired → reset to USERNAME
                self.current_state = AuthState.USERNAME
                self.failed_attempts = 0
                self.locked_until = None
                self.data.pop("locked_until", None)
            else:
                # Still locked
                return self._create_response(authenticated=False)
        
        # GREETING state
        if self.current_state == AuthState.GREETING:
            # First interaction: show greeting and ask for username
            self.current_state = AuthState.USERNAME
        
        # USERNAME state
        elif self.current_state == AuthState.USERNAME:
            # Parse and validate username
            username = self._parse_username(user_input)
            
            if not self._validate_username(username):
                # Validation failed
                self.data["username_error"] = "Bitte gib einen gültigen Benutzernamen ein (mindestens 2 Zeichen)."
                return self._create_response(authenticated=False)
            
            # Check DB availability
            if not self.db:
                logger.error("AuthConversation requires database session for user lookup!")
                return {
                    "message": "Systemfehler: Datenbank nicht verfügbar.",
                    "suggestions": [],
                    "auth_state": self.current_state.value,
                    "authenticated": False,
                    "token": None,
                    "data": self.data
                }
            
            # Check if user exists
            user = self._lookup_user(username)
            if not user:
                # User not found
                self.data["username_error"] = f"Benutzer '{username}' nicht gefunden. Hast du dich vertippt?"
                return self._create_response(authenticated=False)
            
            if not user.is_active:
                # User inactive
                self.data["username_error"] = f"Account '{username}' ist deaktiviert. Bitte kontaktiere einen Administrator."
                return self._create_response(authenticated=False)
            
            # User exists and is active → proceed to password
            self.data["username"] = username
            self.data["user_id"] = user.id
            self.data.pop("username_error", None)  # Clear any previous errors
            self.current_state = AuthState.PASSWORD
        
        # PASSWORD state
        elif self.current_state == AuthState.PASSWORD:
            # Verify password
            username = self.data.get("username")
            user = self._lookup_user(username)
            
            if not user:
                # Should not happen (user was validated in USERNAME state)
                logger.error(f"User {username} not found in PASSWORD state!")
                self.current_state = AuthState.USERNAME
                return self._create_response(authenticated=False)
            
            # Verify password
            if verify_password(user_input, user.password_hash):
                # SUCCESS: Password correct
                logger.info(f"User logged in via chat: {username}")
                
                # Update last_login
                user.last_login = datetime.now()
                self.db.commit()
                
                # Generate JWT token
                token = create_access_token(
                    data={"sub": user.username, "role": user.role},
                    expires_delta=timedelta(hours=24)
                )
                
                # Store token and user info
                self.data["token"] = token
                self.data["user_info"] = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_admin": user.is_admin,
                    "permissions": user.permissions
                }
                
                # Reset failed attempts
                self.failed_attempts = 0
                self.data["failed_attempts"] = 0
                
                # Move to AUTHENTICATED state
                self.current_state = AuthState.AUTHENTICATED
                
                return self._create_response(authenticated=True, token=token, user_info=self.data["user_info"])
            
            else:
                # FAILED: Password incorrect
                self.failed_attempts += 1
                self.data["failed_attempts"] = self.failed_attempts
                
                logger.warning(f"Failed login attempt for user {username} (attempt {self.failed_attempts}/{self.MAX_PASSWORD_ATTEMPTS})")
                
                if self.failed_attempts >= self.MAX_PASSWORD_ATTEMPTS:
                    # LOCKOUT: Too many failed attempts
                    self.current_state = AuthState.LOCKED
                    self.locked_until = datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    self.data["locked_until"] = self.locked_until.isoformat()
                    
                    logger.warning(f"User {username} locked out until {self.locked_until}")
                
                return self._create_response(authenticated=False)
        
        # AUTHENTICATED state
        elif self.current_state == AuthState.AUTHENTICATED:
            # Already authenticated → return token again
            token = self.data.get("token")
            user_info = self.data.get("user_info")
            return self._create_response(authenticated=True, token=token, user_info=user_info)
        
        # Update session data
        self.data["current_state"] = self.current_state.value
        
        # Return response
        return self._create_response(authenticated=False)
    
    def _create_response(self, authenticated: bool, token: Optional[str] = None, user_info: Optional[dict] = None) -> Dict[str, Any]:
        """Helper to create consistent response dict."""
        return {
            "message": self.get_message(),
            "suggestions": self.get_suggestions(),
            "auth_state": self.current_state.value,
            "authenticated": authenticated,
            "token": token,
            "user_info": user_info,
            "data": self.data
        }
    
    def _check_lockout_expired(self) -> bool:
        """Check if lockout period has expired."""
        if not self.locked_until:
            return True
        return datetime.now() >= self.locked_until
    
    def _validate_username(self, username: str) -> bool:
        """
        Validate username.
        
        Rules:
        - At least 2 characters
        - No greetings like "Hallo", "Hi"
        """
        if not username or len(username) < 2:
            return False
        
        # Block greeting words
        greeting_words = ["hallo", "hi", "hey", "servus", "moin", "guten tag"]
        name_lower = username.lower().strip()
        
        if name_lower in greeting_words:
            return False
        
        return True
    
    def _parse_username(self, text: str) -> str:
        """Extract username from user input."""
        # Remove common prefixes
        text = re.sub(r'^(ich bin|ich heiße|heißt|mein name ist|ich bin der|ich bin die|name:)\s+', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _lookup_user(self, username: str) -> Optional[User]:
        """
        Lookup user in database (case-insensitive).
        
        Args:
            username: Username to lookup
        
        Returns:
            User object if found, None otherwise
        """
        if not self.db:
            return None
        
        # Try exact match first
        user = self.db.query(User).filter(User.username == username).first()
        if user:
            return user
        
        # Try case-insensitive match
        user = self.db.query(User).filter(User.username.ilike(username)).first()
        return user
    
    def to_dict(self) -> Dict:
        """Export conversation state to dict."""
        return {
            "current_state": self.current_state.value,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict, db_session: Optional[Session] = None) -> "AuthConversation":
        """Create conversation from dict."""
        return cls(session_data=data.get("data", {}), db_session=db_session)
