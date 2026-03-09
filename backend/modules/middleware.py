# v1.0: [MODULE-SYSTEM] FastAPI Middleware — Modul-Lizenzschutz
"""
ModuleLicenseMiddleware: Schützt Modul-Routes vor unlizenziertem Zugriff.

Workflow:
    Request → /api/modules/erp/dashboard
    1. Ist Pfad unter /api/modules/ (aber NICHT /api/modules/license)? → Ja
    2. registry.module_for_route(path) → ErpModule
    3. registry.is_licensed("erp") → True/False
    4. False → HTTP 403 {"detail": "Modul nicht lizenziert", "module": "erp", "locked": true}
    5. True → call_next(request) → normale Verarbeitung

Wichtig:
    - /api/modules/license Endpoints sind AUSGENOMMEN (sonst keine Aktivierung möglich)
    - /api/modules (Manifest-API) ist AUSGENOMMEN (Frontend braucht Liste)
    - Nur /api/modules/{name}/* wird geprüft
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from .registry import ModuleRegistry


class ModuleLicenseMiddleware(BaseHTTPMiddleware):
    """
    Middleware zum Schutz von Modul-Routes.
    
    Prüft ob ein Modul lizenziert ist bevor der Request durchgelassen wird.
    Unlizenzierte Module erhalten HTTP 403.
    """
    
    def __init__(self, app, registry: ModuleRegistry):
        """
        Args:
            app: ASGI-App
            registry: ModuleRegistry-Instanz
        """
        super().__init__(app)
        self.registry = registry
        logger.info("ModuleLicenseMiddleware aktiviert")
    
    async def dispatch(self, request: Request, call_next):
        """
        Prüft jeden Request auf Modul-Lizenz.
        
        Ausnahmen:
            - /api/modules/license (Aktivierungs-Endpoint)
            - /api/modules (Manifest-API)
            - Pfade außerhalb von /api/modules/
        """
        path = request.url.path
        
        # Prüfe nur Pfade unter /api/modules/{name}/
        if not path.startswith("/api/modules/"):
            return await call_next(request)
        
        # Meta-Endpoints durchlassen (license, manifest)
        # /api/modules oder /api/modules/license oder /api/modules/license/{module}
        if path == "/api/modules" or path.startswith("/api/modules/license"):
            return await call_next(request)
        
        # Modul-Name extrahieren
        module = self.registry.module_for_route(path)
        
        if not module:
            # Pfad passt nicht zu einem registrierten Modul → durchlassen
            # (FastAPI 404 wird später geworfen)
            return await call_next(request)
        
        # Lizenz prüfen
        if not self.registry.is_licensed(module.name):
            logger.warning(f"❌ Unlizenziert: {module.name} → {path}")
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Modul '{module.display_name}' ist nicht lizenziert",
                    "module": module.name,
                    "locked": True
                }
            )
        
        # Lizenziert → durchlassen
        return await call_next(request)
