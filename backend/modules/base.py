# v1.0: [MODULE-SYSTEM] Base Classes für VERA Module
"""
VeraModule: Abstract Base Class für alle VERA-Module
TabConfig: Datenklasse für UI-Tabs

Jedes VERA-Modul (ERP, QM, etc.) erbt von VeraModule und implementiert:
- get_routes() → FastAPI Router
- get_ui_tabs() → Sidebar-Tabs für Frontend
- on_activate() / on_deactivate() → Lifecycle Hooks
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from fastapi import APIRouter


@dataclass(frozen=True)
class TabConfig:
    """
    Konfiguration für einen Sidebar-Tab im Frontend.
    
    Attributes:
        id: Eindeutige Tab-ID (z.B. "erp-dashboard")
        label: Anzeigename (z.B. "Dashboard")
        icon: Emoji oder Icon-Name (z.B. "💰")
        route: Frontend-Route (z.B. "/erp/dashboard")
        order: Sortierreihenfolge in der Sidebar (niedrigere Zahlen zuerst)
    """
    id: str
    label: str
    icon: str
    route: str
    order: int = 100


class VeraModule(ABC):
    """
    Abstract Base Class für VERA-Module.
    
    Jedes Modul muss folgende Eigenschaften definieren:
    - name: Eindeutiger Modulname (lowercase, z.B. "erp")
    - version: Semver-String (z.B. "1.0.0")
    - display_name: Anzeigename für UI (z.B. "VERA ERP")
    - description: Kurzbeschreibung
    - icon: Emoji für UI (z.B. "💰")
    - required_license: Lizenz-Key der benötigt wird (z.B. "erp")
    
    Beispiel:
        class ErpModule(VeraModule):
            name = "erp"
            version = "1.0.0"
            display_name = "VERA ERP"
            description = "Finanzauswertungen und DATEV-Export"
            icon = "💰"
            required_license = "erp"
            
            def get_routes(self) -> list[APIRouter]:
                return [erp_router]
            
            def get_ui_tabs(self) -> list[TabConfig]:
                return [
                    TabConfig("erp-dashboard", "Dashboard", "📊", "/erp/dashboard", 10),
                    TabConfig("erp-reports", "Berichte", "📄", "/erp/reports", 20)
                ]
    """
    
    # Muss von Subclass gesetzt werden
    name: str
    version: str
    display_name: str
    description: str
    icon: str
    required_license: str
    
    @abstractmethod
    def get_routes(self) -> list[APIRouter]:
        """
        Gibt FastAPI-Router für dieses Modul zurück.
        Diese werden unter /api/modules/{name}/ gemountet.
        
        Returns:
            Liste von APIRouter-Objekten
        """
        pass
    
    @abstractmethod
    def get_ui_tabs(self) -> list[TabConfig]:
        """
        Gibt UI-Tab-Konfigurationen für die Sidebar zurück.
        
        Returns:
            Liste von TabConfig-Objekten
        """
        pass
    
    def on_activate(self) -> None:
        """
        Lifecycle Hook: Wird aufgerufen wenn das Modul lizenziert wird.
        Optional zu implementieren.
        
        Nutze dies für:
        - Datenbank-Migrationen
        - Cache-Initialisierung
        - Feature-Flags setzen
        """
        pass
    
    def on_deactivate(self) -> None:
        """
        Lifecycle Hook: Wird aufgerufen wenn die Lizenz entfernt wird.
        Optional zu implementieren.
        
        Nutze dies für:
        - Cleanup von temporären Daten
        - Cache leeren
        - Verbindungen schließen
        """
        pass
    
    def to_manifest(self, licensed: bool) -> dict:
        """
        Generiert Modul-Manifest für Frontend.
        
        Args:
            licensed: Ist das Modul aktuell lizenziert?
        
        Returns:
            Dict mit Modul-Metadaten
        """
        return {
            "name": self.name,
            "version": self.version,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "licensed": licensed,
            "required_license": self.required_license,
            "tabs": [
                {
                    "id": tab.id,
                    "label": tab.label,
                    "icon": tab.icon,
                    "route": tab.route,
                    "order": tab.order
                }
                for tab in self.get_ui_tabs()
            ]
        }
