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
    GET  /api/modules                   -> Liste aller Module + Lizenzstatus
    POST /api/modules/license           -> Lizenz aktivieren
    DELETE /api/modules/license/{mod}   -> Lizenz deaktivieren
"""

from typing import Optional
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from .base import VeraModule
from .license import LicenseStore
from backend.api.auth import get_current_user


class ModuleRegistry:
    """
    Singleton zur Verwaltung aller VERA-Module.
    """

    def __init__(self, license_store: LicenseStore, promo_store=None):
        """
        Args:
            license_store: LicenseStore-Instanz für Lizenzvalidierung
            promo_store: PromoStore-Instanz (optional, für Promo-Code-Unlock)
        """
        self._modules: dict[str, VeraModule] = {}
        self._license_store = license_store
        self._promo_store = promo_store
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
            logger.info(f"Modul '{module.name}' ist lizenziert -> on_activate()")
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
    
    def is_licensed(self, module_name: str, user=None) -> bool:
        """
        Prüft ob ein Modul für den User freigeschaltet ist.
        Prüft users.modules_unlocked in der DB (Promo-Code-System).

        Args:
            module_name: Modul-Name (z.B. "erp")
            user: User-Objekt (optional, für Admin-Check)

        Returns:
            True wenn freigeschaltet, False sonst
        """
        # Admin override
        if user and hasattr(user, 'is_admin') and user.is_admin:
            return True

        # Check user's modules_unlocked in DB
        try:
            import json
            from backend.db.database import SessionLocal
            from backend.models.user import User as UserModel
            db = SessionLocal()
            try:
                db_user = (
                    db.query(UserModel).filter(UserModel.pin_hash.isnot(None)).first()
                    or db.query(UserModel).filter(UserModel.is_admin.is_(True)).first()
                )
                if not db_user:
                    return False
                unlocked = json.loads(db_user.modules_unlocked or '[]')
                return module_name.lower() in unlocked
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"is_licensed DB check failed for {module_name}: {e}")
            return False
    
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
    
    def manifests(self, user=None) -> list[dict]:
        """
        Generiert Modul-Manifeste für Frontend.
        
        Args:
            user: User-Objekt (optional, für Admin-Check)
        
        Returns:
            Liste von Modul-Manifesten (JSON)
        """
        return [
            module.to_manifest(licensed=self.is_licensed(module.name, user=user))
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
                app.include_router(router, prefix=prefix, tags=[module.display_name], dependencies=[Depends(get_current_user)])
                logger.info(f"Routes gemountet: {prefix} ({module.display_name})")
    
    def create_api_router(self) -> APIRouter:
        """
        Erzeugt Meta-API-Router für Modul-Verwaltung.
        
        Endpoints:
            GET  /api/modules              -> Manifest-Liste
            POST /api/modules/license      -> Lizenz aktivieren
            DELETE /api/modules/license/{module} -> Lizenz deaktivieren
        
        Returns:
            APIRouter
        """
        router = APIRouter(prefix="/api/modules", tags=["Module"])
        
        @router.get("")
        async def list_modules(current_user=None):
            """
            Gibt alle Module mit Lizenzstatus zurück.
            Frontend nutzt dies für dynamische Sidebar.
            
            ADMIN OVERRIDE: Admin-User sehen alle Module als lizenziert!
            """
            # TODO: current_user via Depends() injection (later)
            # For now: Return all as licensed (temp fix)
            return self.manifests(user=current_user)
        
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
                logger.info(f"Lizenz aktiviert -> on_activate() für {module_name}")
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
                logger.info(f"Lizenz deaktivieren -> on_deactivate() für {module}")
                mod.on_deactivate()

            success = self._license_store.deactivate(module)

            if not success:
                raise HTTPException(status_code=404, detail=f"Modul '{module}' hat keine Lizenz")

            return {
                "success": True,
                "message": f"Lizenz für '{module}' deaktiviert"
            }

        @router.get("/status")
        async def module_status():
            """
            Gibt Freischalt-Status aller Module zurück.
            Frontend nutzt dies nach PIN-Auth um unlocked-Liste zu aktualisieren.
            """
            import json
            try:
                from backend.db.database import SessionLocal
                from backend.models.user import User as UserModel
                db = SessionLocal()
                try:
                    db_user = (
                        db.query(UserModel).filter(UserModel.pin_hash.isnot(None)).first()
                        or db.query(UserModel).filter(UserModel.is_admin.is_(True)).first()
                    )
                    unlocked = json.loads(db_user.modules_unlocked or '[]') if db_user else []
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"module_status DB error: {e}")
                unlocked = []

            modules = {}
            for mod in self.all_modules():
                modules[mod.name] = {"unlocked": mod.name in unlocked, "display_name": mod.display_name}

            return {"modules": modules, "initialized": True}

        class PromoUnlockRequest(BaseModel):
            promo_code: str

        @router.post("/unlock")
        async def unlock_with_promo(req: PromoUnlockRequest):
            """
            Schaltet Module per Promo-Code frei.
            Speichert die Module in users.modules_unlocked.
            """
            import json

            # PromoStore nutzen wenn vorhanden, sonst direkte Datei-Prüfung
            if self._promo_store:
                valid, modules_to_unlock, msg = self._promo_store.validate(req.promo_code)
                if not valid:
                    raise HTTPException(status_code=404, detail=msg)
            else:
                from pathlib import Path
                promo_db_path = Path(__file__).parent.parent.parent / "data" / "promo_codes.json"
                if not promo_db_path.exists():
                    raise HTTPException(status_code=404, detail="Kein Promo-Code System gefunden")
                with open(promo_db_path, "r", encoding="utf-8") as f:
                    codes = json.load(f)
                code = req.promo_code.strip().upper()
                if code not in codes:
                    raise HTTPException(status_code=404, detail="Ungültiger Promo-Code")
                entry = codes[code]
                if not entry.get("active", True):
                    raise HTTPException(status_code=410, detail="Promo-Code deaktiviert")
                used = entry.get("used", 0)
                max_uses = entry.get("max_uses", 1)
                if used >= max_uses:
                    raise HTTPException(status_code=410, detail="Promo-Code vollständig eingelöst")
                modules_to_unlock = entry.get("modules", [])

            # Save to user's modules_unlocked in DB
            try:
                from backend.db.database import SessionLocal
                from backend.models.user import User as UserModel
                db = SessionLocal()
                try:
                    db_user = (
                        db.query(UserModel).filter(UserModel.pin_hash.isnot(None)).first()
                        or db.query(UserModel).filter(UserModel.is_admin.is_(True)).first()
                    )
                    if not db_user:
                        raise HTTPException(status_code=404, detail="VERA ist noch nicht eingerichtet")
                    unlocked = json.loads(db_user.modules_unlocked or '[]')
                    for mod in modules_to_unlock:
                        if mod not in unlocked:
                            unlocked.append(mod)
                    db_user.modules_unlocked = json.dumps(unlocked)
                    db.commit()
                finally:
                    db.close()
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Fehler beim Speichern der Module: {e}")
                raise HTTPException(status_code=500, detail="Fehler beim Freischalten")

            logger.success(f"Promo-Code eingelöst → Module: {modules_to_unlock}")
            return {
                "success": True,
                "message": f"Module freigeschaltet: {', '.join(modules_to_unlock).upper()}",
                "modules": unlocked,           # Alle freigeschalteten Module (für Session-Update)
                "modules_unlocked": unlocked   # Alias für Rückwärtskompatibilität
            }

        return router
