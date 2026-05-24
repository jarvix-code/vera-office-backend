# v1.0: [QM] Module Definition
"""
QmModule: VERA QM Plugin.

Registriert sich im ModuleRegistry und mountet:
- API-Routes unter /api/modules/qm/
- 5 UI-Tabs in der Sidebar:
    [LIST] QM Übersicht -> /qm/dashboard    (order 300)
    [BOOK] QM-Handbuch  -> /qm/handbook     (order 310)
    [OK] Audits       -> /qm/audits       (order 320)
    [CLEANUP] Hygiene      -> /qm/hygiene      (order 330)
    [OK] Compliance   -> /qm/compliance   (order 340)

Lifecycle:
- on_activate(): Erstellt DB-Tabellen (falls nicht vorhanden)
- on_deactivate(): Nichts (Daten bleiben erhalten)
"""

from fastapi import APIRouter
from loguru import logger

from backend.modules.base import VeraModule, TabConfig
from .router import router as qm_router


class QmModule(VeraModule):
    """
    VERA QM — Qualitätsmanagement für Zahnarztpraxen.
    
    Features:
    - QM-Handbuch: 13 BLZK-Kapitel (Arbeitssicherheit, QM, Handbuch)
    - Dokumentenlenkung: Versionierung, Freigabe-Workflow
    - Audits: Internes Audit mit 10 Default-Fragen
    - Hygiene-Protokolle: Tägliche/wöchentliche Checklisten
    - Compliance-Checks: Nachweise pro Grundelement
    """
    
    name = "qm"
    version = "1.0.0"
    display_name = "VERA QM"
    description = "Qualitätsmanagement nach BLZK — Handbuch, Audits, Hygiene, Compliance"
    icon = "[LIST]"
    required_license = "qm"
    
    def get_routes(self) -> list[APIRouter]:
        """
        Gibt FastAPI-Router zurück.
        Wird unter /api/modules/qm/ gemountet.
        """
        return [qm_router]
    
    def get_ui_tabs(self) -> list[TabConfig]:
        """
        Gibt 5 Sidebar-Tabs zurück.
        """
        return [
            TabConfig(
                id="qm-dashboard",
                label="QM Übersicht",
                icon="[LIST]",
                route="/qm/dashboard",
                order=300
            ),
            TabConfig(
                id="qm-handbook",
                label="QM-Handbuch",
                icon="[BOOK]",
                route="/qm/handbook",
                order=310
            ),
            TabConfig(
                id="qm-audits",
                label="Audits",
                icon="[OK]",
                route="/qm/audits",
                order=320
            ),
            TabConfig(
                id="qm-hygiene",
                label="Hygiene",
                icon="[CLEANUP]",
                route="/qm/hygiene",
                order=330
            ),
            TabConfig(
                id="qm-compliance",
                label="Compliance",
                icon="[OK]",
                route="/qm/compliance",
                order=340
            )
        ]
    
    def on_activate(self) -> None:
        """
        Lifecycle Hook: Modul wurde lizenziert.
        Erstellt DB-Tabellen (falls nicht vorhanden).
        """
        logger.info("QM-Modul aktiviert -> Erstelle DB-Tabellen")
        
        try:
            from backend.db.database import engine
            from .models import Base
            
            # Erstelle Tabellen (idempotent)
            Base.metadata.create_all(bind=engine)
            
            logger.success("QM-Tabellen erstellt: qm_documents, qm_audits, qm_hygiene_protocols, qm_compliance_checks")
        except Exception as e:
            logger.error(f"QM on_activate fehlgeschlagen: {e}")
    
    def on_deactivate(self) -> None:
        """
        Lifecycle Hook: Lizenz wurde entfernt.
        Daten bleiben erhalten (nur Zugriff gesperrt).
        """
        logger.info("QM-Modul deaktiviert (Daten bleiben erhalten)")


# Singleton-Instanz für Registry-Registrierung
qm_module = QmModule()
