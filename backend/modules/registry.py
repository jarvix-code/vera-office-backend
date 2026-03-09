# v1.0: [MODULE-SYSTEM] ModuleRegistry — Plugin-Verwaltung
"""
ModuleRegistry: Singleton zur Verwaltung aller VERA-Module.

Aufgaben:
- Module registrieren (explizit, kein Auto-Discovery)
- Routes unter /api/modules/{name}/ mounten
- Lizenzstatus abfragen (delegiert an LicenseStore)
- Manifest-API für Frontend (/api/modules)
- Lifecycle Hooks (on_activate/on_deactivate)

Workflow:
    registry = ModuleRegistry(license_store)
    registry.register(ErpModule())      # Feuert on_activate() wenn lizenziert
    registry.mount_all(app)             # Mounted Routes
    app.include_router(registry.create_api_router())  # Meta-Endpoints

Meta-Endpoints:
    GET  /api/modules                   → Liste aller Module + Lizenzstatus
    POST /api/modules/license           → Lizenz aktivieren
    DELETE /api/modules/license/{mod}   → Lizenz deaktivieren
"""

from typing import Optional
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from .base import VeraModule
from .license import LicenseStore


class ModuleRegistry:
    """
    Singleton zur Verwaltung aller VERA-Module.
    """
    
    def __init__(self, license_store: LicenseStore):
        """
        Args:
            license_store: LicenseStore-Instanz für Lizenzvalidierung
        """
        self._modules: dict[str, VeraModule] = {}
        self._license_store = license_store
        logger.info("ModuleRegistry initialisiert")
    
    def register(self, module: VeraModule):
        """
        Registriert ein Modul.
        
        Prüft auf Duplikate, loggt die Registrierung und feuert on_activate()
        wenn das Modul bereits lizenziert ist.
        
        Args:
            module: VeraModule-Instanz
        
        Raises:
            ValueError: Wenn Modul-Name bereits registriert
        """
        if module.name in self._modules:
            raise ValueError(f"Modul '{module.name}' ist bereits registriert")
        
        self._modules[module.name] = module
        logger.info(f"Modul registriert: {module.display_name} ({module.version})")
        
        # Lifecycle Hook: on_activate wenn bereits lizenziert
        if self.is_licensed(module.name):
            logger.info(f"Modul '{module.name}' ist lizenziert → on_activate()")
            module.on_activate()
    
    def get(self, name: str) -> Optional[VeraModule]:
        """
        Gibt ein Modul zurück (oder None).
        
        Args:
            name: Modul-Name (z.B. "erp")
        
        Returns:
            VeraModule oder None
        """
        return self._modules.get(name)
    
    def all_modules(self) -> list[VeraModule]:
        """
        Gibt alle registrierten Module zurück.
        
        Returns:
            Liste von VeraModule
        """
        return list(self._modules.values())
    
    def is_licensed(self, module_name: str) -> bool:
        """
        Prüft ob ein Modul lizenziert ist (delegiert an LicenseStore).
        
        Args:
            module_name: Modul-Name (z.B. "erp")
        
        Returns:
            True wenn lizenziert, False sonst
        """
        return self._license_store.is_licensed(module_name)
    
    def module_for_route(self, path: str) -> Optional[VeraModule]:
        """
        Findet das Modul für einen Request-Pfad.
        Wird von der Middleware genutzt.
        
        Args:
            path: Request-Pfad (z.B. "/api/modules/erp/dashboard")
        
        Returns:
            VeraModule oder None
        """
        # Pfad muss mit /api/modules/ beginnen
        if not path.startswith("/api/modules/"):
            return None
        
        # Extrahiere Modul-Name (Teil nach /api/modules/)
        parts = path.split("/")
        if len(parts) < 4:  # /api/modules/{name}/...
            return None
        
        module_name = parts[3]
        return self.get(module_name)
    
    def manifests(self) -> list[dict]:
        """
        Generiert Modul-Manifeste für Frontend.
        
        Returns:
            Liste von Modul-Manifesten (JSON)
        """
        return [
            module.to_manifest(licensed=self.is_licensed(module.name))
            for module in self.all_modules()
        ]
    
    def mount_all(self, app: FastAPI):
        """
        Mounted alle Modul-Routes unter /api/modules/{name}/.
        
        Args:
            app: FastAPI-Instanz
        """
        for module in self.all_modules():
            for router in module.get_routes():
                prefix = f"/api/modules/{module.name}"
                app.include_router(router, prefix=prefix, tags=[module.display_name])
                logger.info(f"Routes gemountet: {prefix} ({module.display_name})")
    
    def create_api_router(self) -> APIRouter:
        """
        Erzeugt Meta-API-Router für Modul-Verwaltung.
        
        Endpoints:
            GET  /api/modules              → Manifest-Liste
            POST /api/modules/license      → Lizenz aktivieren
            DELETE /api/modules/license/{module} → Lizenz deaktivieren
        
        Returns:
            APIRouter
        """
        router = APIRouter(prefix="/api/modules", tags=["Module"])
        
        @router.get("")
        async def list_modules():
            """
            Gibt alle Module mit Lizenzstatus zurück.
            Frontend nutzt dies für dynamische Sidebar.
            """
            return self.manifests()
        
        class LicenseActivateRequest(BaseModel):
            key: str
        
        @router.post("/license")
        async def activate_license(req: LicenseActivateRequest):
            """
            Aktiviert eine Lizenz.
            
            Body: {"key": "VERA-ERP-eyJt..."}
            
            Returns:
                {"success": true, "message": "...", "module": "erp"}
            """
            success, message = self._license_store.activate(req.key)
            
            if not success:
                raise HTTPException(status_code=400, detail=message)
            
            # Extrahiere Modul-Name aus Key
            # Format: VERA-{MODULE}-{body}
            import re
            match = re.match(r'^VERA-([A-Z]+)-', req.key, re.IGNORECASE)
            module_name = match.group(1).lower() if match else "unknown"
            
            # Lifecycle Hook: on_activate
            module = self.get(module_name)
            if module:
                logger.info(f"Lizenz aktiviert → on_activate() für {module_name}")
                module.on_activate()
            
            return {
                "success": True,
                "message": message,
                "module": module_name
            }
        
        @router.delete("/license/{module}")
        async def deactivate_license(module: str):
            """
            Deaktiviert eine Lizenz.
            
            Params:
                module: Modul-Name (z.B. "erp")
            
            Returns:
                {"success": true, "message": "..."}
            """
            # Lifecycle Hook: on_deactivate
            mod = self.get(module)
            if mod:
                logger.info(f"Lizenz deaktivieren → on_deactivate() für {module}")
                mod.on_deactivate()
            
            success = self._license_store.deactivate(module)
            
            if not success:
                raise HTTPException(status_code=404, detail=f"Modul '{module}' hat keine Lizenz")
            
            return {
                "success": True,
                "message": f"Lizenz für '{module}' deaktiviert"
            }
        
        return router
