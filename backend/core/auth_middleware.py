"""
Auth-Middleware für VERA Office
Prüft JWT Token nur für explizit geschützte Routen (QM, ERP, DATEV, Admin).
Alle anderen Routen sind öffentlich zugänglich.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from backend.api.auth import decode_access_token
from backend.db.database import SessionLocal
from backend.models.user import User


# Nur diese Routen brauchen Auth (Prefix-basiert)
PROTECTED_PREFIXES = [
    "/api/qm/",
    "/api/erp/",
    "/api/datev/",
    "/api/admin/",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware: Alle Routen sind öffentlich AUSSER PROTECTED_PREFIXES.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Nicht-API-Routen und Static Files immer durchlassen
        if not path.startswith("/api"):
            return await call_next(request)

        # Prüfe ob Route geschützt ist
        if not self._is_protected_route(path):
            return await call_next(request)

        # Ab hier: geschützte Route → Auth erforderlich
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"🔒 Auth failed for {request.method} {path}: Missing authorization header")
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
                else:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "User not found or inactive"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
            finally:
                db.close()

        return await call_next(request)

    def _is_protected_route(self, path: str) -> bool:
        for prefix in PROTECTED_PREFIXES:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                return True
        return False
