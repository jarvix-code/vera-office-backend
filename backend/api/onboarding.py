"""
VERA Office - Onboarding API
Ersteinrichtungs-Wizard für VERA Office
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.db.database import get_db
from backend.models.settings import OnboardingState, Settings
from backend.models.category import Category
from backend.config import config
from backend.core.ai.filer import filer
from backend.core.folder_manager import folder_manager

router = APIRouter()


# Request/Response Models
class CompanyProfile(BaseModel):
    """Firmenprofil (Schritt 1)"""
    company_type: str  # Praxis, Handwerk, Büro, Handel, Gastronomie
    industry: str  # z.B. "Zahnarztpraxis", "Handwerksbetrieb"
    employee_range: str  # z.B. "1-5", "6-20", "21-50"


class DocumentType(BaseModel):
    """Dokumenttyp"""
    name: str
    display_name: str
    storage_path: str
    retention_years: Optional[int] = None
    keywords: Optional[str] = None


class NetworkConfig(BaseModel):
    """Netzwerk-Konfiguration (Schritt 3)"""
    internet_enabled: bool
    email_enabled: bool
    email_host: Optional[str] = None
    email_port: Optional[int] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    network_shares: Optional[List[str]] = []


class OnboardingStep1Request(BaseModel):
    """Schritt 1: Unternehmens-Profil"""
    profile: CompanyProfile


class OnboardingStep2Request(BaseModel):
    """Schritt 2: Dokumenttypen"""
    document_types: List[DocumentType]


class OnboardingStep3Request(BaseModel):
    """Schritt 3: Netzwerk"""
    network: NetworkConfig


class OnboardingStatusResponse(BaseModel):
    """Onboarding-Status"""
    completed: bool
    current_step: int
    total_steps: int
    company_profile: Optional[dict] = None
    document_types: Optional[list] = None
    network_config: Optional[dict] = None


# Vordefinierte Dokumenttypen nach Branche
DOCUMENT_TYPES_BY_INDUSTRY = {
    "Zahnarztpraxis": [
        {"name": "rechnung_eingang", "display_name": "Eingangsrechnungen", "storage_path": "Finanzen/Rechnungen/Eingang", "retention_years": 10, "keywords": "Rechnung,Invoice,RE-"},
        {"name": "rechnung_ausgang", "display_name": "Ausgangsrechnungen", "storage_path": "Finanzen/Rechnungen/Ausgang", "retention_years": 10},
        {"name": "personal", "display_name": "Personalakten", "storage_path": "Personal/Akten", "retention_years": None},
        {"name": "vertraege", "display_name": "Verträge", "storage_path": "Verträge", "retention_years": None},
        {"name": "behoerde", "display_name": "Behördenschreiben", "storage_path": "Behörden", "retention_years": 10},
        {"name": "qm", "display_name": "QM-Dokumente", "storage_path": "Qualitätsmanagement", "retention_years": None},
        {"name": "labor", "display_name": "Laboraufträge", "storage_path": "Labor", "retention_years": 5},
    ],
    "Handwerksbetrieb": [
        {"name": "rechnung_eingang", "display_name": "Eingangsrechnungen", "storage_path": "Finanzen/Rechnungen/Eingang", "retention_years": 10},
        {"name": "rechnung_ausgang", "display_name": "Ausgangsrechnungen", "storage_path": "Finanzen/Rechnungen/Ausgang", "retention_years": 10},
        {"name": "personal", "display_name": "Personalakten", "storage_path": "Personal/Akten", "retention_years": None},
        {"name": "vertraege", "display_name": "Verträge", "storage_path": "Verträge", "retention_years": None},
        {"name": "behoerde", "display_name": "Behördenschreiben", "storage_path": "Behörden", "retention_years": 10},
        {"name": "angebote", "display_name": "Angebote", "storage_path": "Angebote", "retention_years": 2},
    ],
    "default": [
        {"name": "rechnung_eingang", "display_name": "Eingangsrechnungen", "storage_path": "Finanzen/Rechnungen/Eingang", "retention_years": 10},
        {"name": "rechnung_ausgang", "display_name": "Ausgangsrechnungen", "storage_path": "Finanzen/Rechnungen/Ausgang", "retention_years": 10},
        {"name": "personal", "display_name": "Personalakten", "storage_path": "Personal/Akten", "retention_years": None},
        {"name": "vertraege", "display_name": "Verträge", "storage_path": "Verträge", "retention_years": None},
        {"name": "behoerde", "display_name": "Behördenschreiben", "storage_path": "Behörden", "retention_years": 10},
    ]
}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(db: Session = Depends(get_db)):
    """
    Gibt aktuellen Onboarding-Status zurück
    """
    state = db.query(OnboardingState).first()
    
    if not state:
        # Erstelle initialen State
        state = OnboardingState(
            completed=False,
            current_step=1,
            total_steps=6  # Profil, Dokumenttypen, Netzwerk, Lizenz, Complete
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    
    return OnboardingStatusResponse(
        completed=state.completed,
        current_step=state.current_step,
        total_steps=state.total_steps,
        company_profile=state.company_profile,
        document_types=state.document_types,
        network_config=state.network_config
    )


@router.post("/step1")
async def onboarding_step1(request: OnboardingStep1Request, db: Session = Depends(get_db)):
    """
    Schritt 1: Unternehmens-Profil speichern
    """
    state = db.query(OnboardingState).first()
    if not state:
        state = OnboardingState()
        db.add(state)
    
    state.company_profile = request.profile.model_dump()
    state.current_step = 2
    db.commit()
    
    return {"status": "ok", "next_step": 2}


@router.get("/step2/suggestions")
async def get_document_type_suggestions(db: Session = Depends(get_db)):
    """
    Gibt Dokumenttyp-Vorschläge basierend auf Branche zurück
    """
    state = db.query(OnboardingState).first()
    
    if not state or not state.company_profile:
        # Default-Liste
        return {"suggestions": DOCUMENT_TYPES_BY_INDUSTRY["default"]}
    
    industry = state.company_profile.get("industry", "default")
    suggestions = DOCUMENT_TYPES_BY_INDUSTRY.get(industry, DOCUMENT_TYPES_BY_INDUSTRY["default"])
    
    return {"suggestions": suggestions}


@router.post("/step2")
async def onboarding_step2(request: OnboardingStep2Request, db: Session = Depends(get_db)):
    """
    Schritt 2: Dokumenttypen speichern und Kategorien erstellen
    """
    state = db.query(OnboardingState).first()
    if not state:
        raise HTTPException(status_code=400, detail="Onboarding nicht gestartet")
    
    # Speichere Dokumenttypen
    state.document_types = [dt.model_dump() for dt in request.document_types]
    state.current_step = 3
    
    # Erstelle Kategorien in DB
    for doc_type in request.document_types:
        existing = db.query(Category).filter(Category.name == doc_type.name).first()
        if not existing:
            category = Category(
                name=doc_type.name,
                display_name=doc_type.display_name,
                storage_path=doc_type.storage_path,
                retention_years=doc_type.retention_years,
                keywords=doc_type.keywords,
                is_system=True  # Von Onboarding = System-Kategorie
            )
            db.add(category)
    
    db.commit()
    
    # Branchenspezifische Extra-Kategorien in DB anlegen (Wissen, keine Ordner!)
    industry = "allgemein"
    if state.company_profile:
        industry = state.company_profile.get("industry", "allgemein")
    
    try:
        structure = folder_manager.generate_structure(industry)
        
        # Nur DB-Kategorien anlegen, KEINE physischen Ordner
        # Ordner werden on-demand angelegt wenn Dokumente abgelegt werden
        for extra_cat in structure.get("extra_categories", []):
            existing = db.query(Category).filter(Category.name == extra_cat["name"]).first()
            if not existing:
                category = Category(
                    name=extra_cat["name"],
                    display_name=extra_cat["display_name"],
                    storage_path=extra_cat["storage_path"],
                    retention_years=extra_cat.get("retention_years"),
                    keywords=extra_cat.get("keywords"),
                    is_system=True,
                )
                db.add(category)
        db.commit()
        
        from loguru import logger
        logger.info(f"✅ Ordnerstruktur-Wissen geladen für Branche '{industry}' (Ordner werden on-demand erstellt)")
    except Exception as e:
        from loguru import logger
        logger.error(f"❌ Fehler bei Ordnerstruktur-Setup: {e}")
    
    return {"status": "ok", "next_step": 3}


@router.post("/step3")
async def onboarding_step3(request: OnboardingStep3Request, db: Session = Depends(get_db)):
    """
    Schritt 3: Netzwerk-Konfiguration speichern
    """
    state = db.query(OnboardingState).first()
    if not state:
        raise HTTPException(status_code=400, detail="Onboarding nicht gestartet")
    
    state.network_config = request.network.model_dump()
    state.current_step = 4  # Nächster Schritt: Lizenz-Aktivierung
    
    # Speichere Einstellungen
    settings_data = [
        ("internet_enabled", str(request.network.internet_enabled), "bool", "network"),
        ("email_enabled", str(request.network.email_enabled), "bool", "network"),
    ]
    
    if request.network.email_enabled and request.network.email_host:
        settings_data.extend([
            ("email_host", request.network.email_host, "string", "network"),
            ("email_port", str(request.network.email_port), "int", "network"),
            ("email_username", request.network.email_username or "", "string", "network"),
            ("email_password", request.network.email_password or "", "string", "network"),
        ])
    
    for key, value, value_type, category in settings_data:
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
            setting.value_type = value_type
        else:
            setting = Settings(key=key, value=value, value_type=value_type, category=category)
            db.add(setting)
    
    db.commit()
    
    return {"status": "ok", "next_step": 4}


@router.post("/connection-test")
async def test_connection():
    """
    Testet HTTPS-Verbindung zum Update-Server
    
    Returns:
        {
            "reachable": true/false,
            "message": "Menschliche Nachricht",
            "server_url": "https://updates.vera-office.de",
            "latency_ms": 123
        }
    """
    import aiohttp
    import time
    
    server_url = config.UPDATE_SERVER if hasattr(config, 'UPDATE_SERVER') else "https://updates.vera-office.de"
    
    try:
        start = time.time()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{server_url}/api/health",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                latency_ms = int((time.time() - start) * 1000)
                
                if response.status == 200:
                    return {
                        "reachable": True,
                        "message": "Verbindung erfolgreich — Updates sind verfügbar",
                        "server_url": server_url,
                        "latency_ms": latency_ms
                    }
                else:
                    return {
                        "reachable": False,
                        "message": f"Server antwortet, aber mit Status {response.status}",
                        "server_url": server_url,
                        "latency_ms": latency_ms
                    }
    
    except aiohttp.ClientError as e:
        logger.warning(f"Update-Server nicht erreichbar: {e}")
        return {
            "reachable": False,
            "message": "Server nicht erreichbar. Bitte prüfen Sie die Internetverbindung. VERA funktioniert trotzdem offline.",
            "server_url": server_url,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Connection-Test fehlgeschlagen: {e}")
        return {
            "reachable": False,
            "message": "Verbindungstest fehlgeschlagen. VERA funktioniert trotzdem offline.",
            "server_url": server_url,
            "error": str(e)
        }


class LicenseActivationRequest(BaseModel):
    """Lizenz-Aktivierung Request"""
    license_key: str
    activate_trial: bool = False  # True wenn Trial statt Key


@router.post("/activate")
async def activate_license(request: LicenseActivationRequest, db: Session = Depends(get_db)):
    """
    Aktiviert Lizenz-Key oder Trial-Lizenz beim Onboarding
    
    Body:
        {
            "license_key": "VERA-...", 
            "activate_trial": false
        }
    
    Returns:
        {
            "success": true,
            "message": "Menschliche Nachricht",
            "license_type": "trial" | "full",
            "valid_until": "2026-03-30" (nur bei Trial),
            "days_remaining": 30
        }
    """
    from pathlib import Path
    from backend.core.license import LicenseService
    
    state = db.query(OnboardingState).first()
    if not state:
        raise HTTPException(status_code=400, detail="Onboarding nicht gestartet")
    
    license_service = LicenseService(Path(config.DATA_DIR))
    
    # Trial-Lizenz aktivieren
    if request.activate_trial:
        try:
            company_name = state.company_profile.get('company_type', 'Trial User') if state.company_profile else 'Trial User'
            trial_result = license_service.create_trial(customer_name=company_name)
            
            return {
                "success": True,
                "message": "30-Tage Testversion aktiviert. Sie können VERA jetzt ausprobieren.",
                "license_type": "trial",
                "valid_until": trial_result.get("valid_until"),
                "days_remaining": trial_result.get("days", 30)
            }
        except Exception as e:
            logger.error(f"Trial-Erstellung fehlgeschlagen: {e}")
            raise HTTPException(
                status_code=500,
                detail="Testversion konnte nicht erstellt werden. Bitte kontaktieren Sie den Support."
            )
    
    # Lizenz-Key aktivieren
    else:
        if not request.license_key or len(request.license_key.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Ungültiger Lizenzschlüssel. Bitte prüfen Sie die Eingabe."
            )
        
        try:
            # Versuche Online-Aktivierung
            company_name = state.company_profile.get('company_type', 'Firma') if state.company_profile else 'Firma'
            result = license_service.activate(
                license_key=request.license_key.strip(),
                customer_name=company_name
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "message": "VERA ist aktiviert! Sie können jetzt alle Funktionen nutzen.",
                    "license_type": "full",
                    "valid_until": result.get("valid_until"),
                    "features": result.get("features", [])
                }
            else:
                error_msg = result.get("error", "Unbekannter Fehler")
                
                # Menschliche Fehlermeldungen
                if "network" in error_msg.lower() or "connection" in error_msg.lower():
                    detail = "Server nicht erreichbar. Prüfen Sie die Internetverbindung und versuchen Sie es erneut."
                elif "invalid" in error_msg.lower() or "signature" in error_msg.lower():
                    detail = "Ungültiger Lizenzschlüssel. Bitte prüfen Sie die Eingabe oder kontaktieren Sie den Support."
                elif "expired" in error_msg.lower():
                    detail = "Diese Lizenz ist abgelaufen. Bitte kontaktieren Sie den Support für eine Verlängerung."
                else:
                    detail = f"Aktivierung fehlgeschlagen: {error_msg}"
                
                raise HTTPException(status_code=400, detail=detail)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Lizenz-Aktivierung fehlgeschlagen: {e}")
            raise HTTPException(
                status_code=500,
                detail="Aktivierung fehlgeschlagen. Bitte versuchen Sie es später erneut oder kontaktieren Sie den Support."
            )


@router.post("/complete")
async def complete_onboarding(db: Session = Depends(get_db)):
    """
    Schließt Onboarding ab (Lizenz muss vorher aktiviert werden!)
    """
    from pathlib import Path
    from backend.core.license import LicenseService
    
    state = db.query(OnboardingState).first()
    if not state:
        raise HTTPException(status_code=400, detail="Onboarding nicht gestartet")
    
    # Prüfe ob Lizenz aktiviert ist
    license_service = LicenseService(Path(config.DATA_DIR))
    if not license_service.license:
        raise HTTPException(
            status_code=400,
            detail="Bitte aktivieren Sie eine Lizenz bevor Sie fortfahren."
        )
    
    state.completed = True
    state.current_step = state.total_steps
    state.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "status": "ok",
        "message": "Onboarding abgeschlossen",
        "license_active": True
    }


class ChatInputRequest(BaseModel):
    """Chat input — either a text message or a special action"""
    input: Optional[str] = None
    action: Optional[str] = None  # e.g. "cert_done"


@router.get("/chat")
async def get_chat_state(db: Session = Depends(get_db)):
    """
    Returns the current conversational onboarding state.
    Used on page load to resume an in-progress conversation.
    """
    from backend.core.ai.onboarding_conversation import OnboardingConversation

    state = db.query(OnboardingState).first()
    chat_data = state.onboarding_chat_data if state else None

    conv = OnboardingConversation(session_data=chat_data)

    return {
        "state": conv.current_state.value,
        "message": conv.get_message(),
        "suggestions": conv.get_suggestions(),
        "input_type": conv.get_input_type(),
        "completed": False,
    }


@router.post("/chat")
async def post_chat_message(request: ChatInputRequest, db: Session = Depends(get_db)):
    """
    Process one step of the conversational onboarding.

    For cert_install step send { "action": "cert_done" }.
    For all other steps send { "input": "<user text>" }.

    On completion (PIN confirmed) this endpoint:
      1. Creates the admin user
      2. Marks onboarding complete
      3. Returns an access token for auto-login
    """
    from backend.core.ai.onboarding_conversation import OnboardingConversation
    from backend.models.user import User
    from backend.api.auth import hash_password, create_access_token
    from datetime import timedelta

    # Load or init conversation
    state = db.query(OnboardingState).first()
    if not state:
        state = OnboardingState(completed=False, current_step=1, total_steps=6)
        db.add(state)
        db.commit()
        db.refresh(state)

    conv = OnboardingConversation(session_data=state.onboarding_chat_data or {})

    # Resolve input: action "cert_done" maps to a special marker
    user_input = request.input or ""
    if request.action == "cert_done":
        user_input = "__cert_done__"

    result = conv.process_input(user_input)

    # Persist updated conversation data
    state.onboarding_chat_data = result["data"]
    db.commit()

    if result.get("completed"):
        # --- Create admin user ---
        data = result["data"]
        user_name = data.get("user_name", "Admin")
        password = data.get("password", "")
        pin = data.get("pin", "")

        # Derive a clean username from the display name
        username = user_name.lower().replace(" ", ".").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        if len(username) < 3:
            username = "admin"

        access_token = None
        user_info = None

        existing_users = db.query(User).count()
        if existing_users == 0 and password:
            password_hash = hash_password(password)
            admin = User(
                username=username,
                password_hash=password_hash,
                full_name=user_name,
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

            # Save PIN to settings
            if pin:
                from backend.models.settings import Settings
                pin_setting = db.query(Settings).filter(Settings.key == "user_pin").first()
                if pin_setting:
                    pin_setting.value = pin
                else:
                    db.add(Settings(key="user_pin", value=pin, value_type="string", category="auth"))
                db.commit()

            access_token = create_access_token(
                data={"sub": admin.username},
                expires_delta=timedelta(hours=24),
            )
            user_info = {
                "id": admin.id,
                "username": admin.username,
                "full_name": admin.full_name,
                "is_admin": admin.is_admin,
            }

        # Mark onboarding complete (skip license check for chat flow)
        state.completed = True
        state.current_step = state.total_steps
        from datetime import datetime
        state.completed_at = datetime.utcnow()
        db.commit()

        return {
            "state": "complete",
            "message": result["message"],
            "suggestions": [],
            "input_type": "done",
            "completed": True,
            "access_token": access_token,
            "user": user_info,
        }

    return {
        "state": result["data"].get("current_state", conv.current_state.value),
        "message": result["message"],
        "suggestions": result.get("suggestions", []),
        "input_type": result.get("input_type", "text"),
        "completed": False,
    }


@router.post("/reset")
async def reset_onboarding(db: Session = Depends(get_db)):
    """
    Setzt Onboarding zurück (nur für Entwicklung/Testing)
    """
    if not config.DEBUG:
        raise HTTPException(status_code=403, detail="Nur im Debug-Modus verfügbar")
    
    # Lösche Onboarding-State
    db.query(OnboardingState).delete()
    
    # Lösche System-Kategorien
    db.query(Category).filter(Category.is_system == True).delete()
    
    # Lösche Einstellungen
    db.query(Settings).filter(Settings.category == "network").delete()
    
    db.commit()
    
    return {"status": "ok", "message": "Onboarding zurückgesetzt"}


@router.get('/languages')
async def get_supported_languages():
    """Supported languages for onboarding - Bug #673 / #674 Fix"""
    return {
        'languages': [
            {'code': 'de', 'name': 'Deutsch', 'flag': 'de'},
            {'code': 'en', 'name': 'English', 'flag': 'gb'}
        ],
        'default': 'de'
    }
