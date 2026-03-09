# v1.0: [ERP] Module Definition
"""
ErpModule: VERA ERP Plugin.

Registriert sich im ModuleRegistry und mountet:
- API-Routes unter /api/modules/erp/
- 3 UI-Tabs in der Sidebar:
    📊 Dashboard     → /erp/dashboard   (order 200)
    📋 Offene Posten → /erp/open-items  (order 210)
    📄 Reports       → /erp/reports     (order 220)

Lifecycle:
- on_activate(): Erstellt DB-Tabellen (falls nicht vorhanden)
- on_deactivate(): Nichts (Daten bleiben erhalten)
"""

from fastapi import APIRouter
from loguru import logger

from backend.modules.base import VeraModule, TabConfig
from .router import router as erp_router


class ErpModule(VeraModule):
    """
    VERA ERP — Finanzauswertungen und DATEV-Export.
    
    Features:
    - Dashboard: Umsatz, Kosten, Cashflow, Vergleiche
    - Offene Posten: Fälligkeiten mit Ampel-System
    - Reports: BWA, USt-Voranmeldung, CSV/DATEV-Export
    - Automatische Extraktion aus klassifizierten Rechnungen
    """
    
    name = "erp"
    version = "1.0.0"
    display_name = "VERA ERP"
    description = "Finanzauswertungen, BWA, USt-Voranmeldung, DATEV-Export"
    icon = "💰"
    required_license = "erp"
    
    def get_routes(self) -> list[APIRouter]:
        """
        Gibt FastAPI-Router zurück.
        Wird unter /api/modules/erp/ gemountet.
        """
        return [erp_router]
    
    def get_ui_tabs(self) -> list[TabConfig]:
        """
        Gibt 3 Sidebar-Tabs zurück.
        """
        return [
            TabConfig(
                id="erp-dashboard",
                label="Finanzen",
                icon="📊",
                route="/erp/dashboard",
                order=200
            ),
            TabConfig(
                id="erp-open-items",
                label="Offene Posten",
                icon="📋",
                route="/erp/open-items",
                order=210
            ),
            TabConfig(
                id="erp-reports",
                label="Reports",
                icon="📄",
                route="/erp/reports",
                order=220
            )
        ]
    
    def on_activate(self) -> None:
        """
        Lifecycle Hook: Modul wurde lizenziert.
        Erstellt DB-Tabellen (falls nicht vorhanden).
        """
        logger.info("ERP-Modul aktiviert → Erstelle DB-Tabellen")
        
        try:
            from backend.db.database import engine
            from .models import Base
            
            # Erstelle Tabellen (idempotent)
            Base.metadata.create_all(bind=engine)
            
            logger.success("✅ ERP-Tabellen erstellt: erp_financial_records")
        except Exception as e:
            logger.error(f"❌ ERP on_activate fehlgeschlagen: {e}")
    
    def on_deactivate(self) -> None:
        """
        Lifecycle Hook: Lizenz wurde entfernt.
        Daten bleiben erhalten (nur Zugriff gesperrt).
        """
        logger.info("ERP-Modul deaktiviert (Daten bleiben erhalten)")


# Singleton-Instanz für Registry-Registrierung
erp_module = ErpModule()
