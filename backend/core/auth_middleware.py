"""
Auth-Middleware für VERA Office
Prüft JWT Token und Rollen-Berechtigungen für geschützte Routen
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from backend.api.auth import decode_access_token
from backend.db.database import SessionLocal
from backend.models.user import User


# Öffentliche Routen (kein Auth erforderlich)
PUBLIC_ROUTES = [
    "/health",
    "/api/health",
    "/api/system/health",
    "/api/system/version",
    "/api/auth/login",
    "/api/auth/chat",  # Conversational Auth Flow (must be public!)
    "/api/agent/chat",  # TEMPORARY DEBUG (Bug #10)
    "/api/feedback/submit",  # User Feedback ohne Login (Bug Reports, Feature Requests)
    "/api/auth/create-user",
    "/api/onboarding/admin/create",
    "/api/onboarding/admin/exists",
    "/api/onboarding/status",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc"
]

# Route -> Required Permission Mapping
ROUTE_PERMISSIONS = {
    # Documents
    "POST /api/documents": "upload",
    "PUT /api/documents": "write",
    "DELETE /api/documents": "delete",
    # Settings
    "GET /api/system/settings": "settings",
    "PUT /api/system/settings": "settings",
    # User management
    "GET /api/auth/users": "users",
    "POST /api/auth/users": "users",
    "PUT /api/auth/users": "users",
    "DELETE /api/auth/users": "users",
    # Scanner
    "POST /api/scanner": "scan",
    # Export
    "GET /api/documents/export": "export",
    # Modules
    "POST /api/modules": "modules",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware für JWT-basierte Authentifizierung mit Rollen-Prüfung.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # Öffentliche Routen durchlassen
        if self._is_public_route(path):
            return await call_next(request)
        
        # Static Files / Frontend durchlassen
        if path.startswith("/static") or path == "/" or not path.startswith("/api"):
            return await call_next(request)
        
        # Authorization Header extrahieren
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"🔒 Auth failed for {method} {path}: Missing authorization header")
            logger.debug(f"  Headers: {dict(request.headers)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authorization header"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Bearer Token extrahieren
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Token dekodieren
        payload = decode_access_token(token)
        if payload is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # User aus DB laden
        username = payload.get("sub")
        if username:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                if user and user.is_active:
                    request.state.user_id = user.id
                    request.state.username = user.username
                    request.state.user_role = user.role
                    request.state.user = user
                    
                    # Rollen-basierte Prüfung
                    required_perm = self._get_required_permission(method, path)
                    if required_perm and not user.has_permission(required_perm):
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": f"Keine Berechtigung: {required_perm}"}
                        )
                else:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User not found or inactive"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            finally:
                db.close()
        
        return await call_next(request)
    
    def _is_public_route(self, path: str) -> bool:
        if path in PUBLIC_ROUTES:
            return True
        if path.startswith("/api/auth/login"):
            return True
        return False
    
    def _get_required_permission(self, method: str, path: str) -> str | None:
        """Ermittelt die benötigte Berechtigung für eine Route."""
        # Exakter Match
        key = f"{method} {path}"
        if key in ROUTE_PERMISSIONS:
            return ROUTE_PERMISSIONS[key]
        
        # Prefix Match (z.B. DELETE /api/documents/123)
        for route_key, perm in ROUTE_PERMISSIONS.items():
            route_method, route_path = route_key.split(" ", 1)
            if method == route_method and path.startswith(route_path):
                return perm
        
        # Default: read-Berechtigung für alle GET-Anfragen
        if method == "GET":
            return "read"
        
        # Für unbekannte Schreib-Routen: write
        if method in ("POST", "PUT", "PATCH"):
            return "write"
        
        return None
