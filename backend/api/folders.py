"""
VERA Office - Folders API
Endpunkte für Ordnerstruktur-Verwaltung
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.db.database import get_db
from backend.models.settings import OnboardingState
from backend.core.folder_manager import folder_manager

router = APIRouter()


@router.get("/structure")
async def get_folder_structure(
    industry: Optional[str] = Query(None, description="Branche (überschreibt Onboarding-Profil)"),
    db: Session = Depends(get_db),
):
    """
    Gibt die aktuelle Ordnerstruktur als JSON zurück.
    Nutzt die Branche aus dem Onboarding-Profil oder den Query-Parameter.
    """
    # Branche ermitteln
    if not industry:
        state = db.query(OnboardingState).first()
        if state and state.company_profile:
            industry = state.company_profile.get("industry", "allgemein")
        else:
            industry = "allgemein"

    structure = folder_manager.generate_structure(industry)
    flat = folder_manager.structure_to_flat_list(structure)
    retention = folder_manager.get_retention_info(structure)

    return {
        "industry": industry,
        "template": structure.get("industry_template"),
        "folders": flat,
        "retention_info": retention,
        "total_folders": len(flat),
    }


@router.get("/templates")
async def list_templates():
    """Gibt alle verfügbaren Branchen-Templates zurück."""
    return {"templates": folder_manager.list_available_templates()}


@router.post("/generate")
async def generate_folders(
    industry: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Generiert die physische Ordnerstruktur auf der Festplatte.
    Nutzt die Branche aus dem Onboarding-Profil oder den Query-Parameter.
    """
    if not industry:
        state = db.query(OnboardingState).first()
        if state and state.company_profile:
            industry = state.company_profile.get("industry", "allgemein")
        else:
            raise HTTPException(400, "Keine Branche angegeben und kein Onboarding-Profil vorhanden")

    structure = folder_manager.generate_structure(industry)
    created = folder_manager.create_folders(structure)

    return {
        "status": "ok",
        "industry": industry,
        "folders_created": len(created),
    }
