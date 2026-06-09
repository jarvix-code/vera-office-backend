"""
VERA Office - FastAPI Backend
Hauptapplikation mit Lifespan, CORS, Health-Endpoints
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import sys
import httpx

from backend.config import config
from backend.db.database import init_db
from backend.core.scanner import HotfolderScanner
from backend.core.mdns import mdns_service
from backend.core.ssl_setup import ensure_ssl_certs
from backend.core.diagnostics import init_diagnostics, get_diagnostics
from backend.core.license_check import check_license_on_startup
from backend.core.auth_middleware import AuthMiddleware
from backend.modules.setup import setup_modules
from backend.api import documents, documents_ai, onboarding, onboarding_admin, system, scanner, agent, folders, auth
from backend.api import discovery, feedback, promo, dashboard, workflow, vera_chat, calendar, settings, dms, ocr
from backend.services.update_client import init_update_client, get_update_client
from backend.services.telemetry_client import init_telemetry_client, get_telemetry_client

# Loguru Setup
logger.remove()  # Entferne Default-Handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    level="DEBUG" if config.DEBUG else "INFO"
)

# Hotfolder-Scanner (global, wird in Lifespan gestartet/gestoppt)
hotfolder_scanner = None


async def process_new_document(file_path):
    """
    Callback fÃ¼r Hotfolder-Scanner: Verarbeitet neue Dokumente
    Wird aufgerufen wenn neue Datei in data/inbox/ landet
    
    Pipeline:
    1. Bildverarbeitung (Kantenerkennung, Perspektivkorrektur, Kontrast)
    2. OCR-Texterkennung
    3. PDF-Generierung mit OCR-Layer
    4. KI-Klassifikation (Category + Confidence)
    5. KI-Namer (Semantic Filename)
    6. Auto-Filing (wenn Confidence >= Threshold)
    7. Datenbank-Eintrag erstellen
    8. Feedback Store (wenn auto-confirmed)
    9. Cleanup (Original + Temp-Dateien lÃ¶schen)
    """
    import time
    from pathlib import Path
    from backend.core.image_processor import ImageProcessor
    from backend.core.ocr_engine import OCREngine
    from backend.core.pdf_generator import PDFGenerator
    from backend.models.document import Document
    from backend.models.category import Category
    from backend.db.database import SessionLocal
    from backend.core.ai.classifier import classifier
    from backend.core.ai.namer import namer
    from backend.core.ai.filer import filer
    from backend.core.ai.feedback_store import feedback_store
    
    try:
        logger.info(f"ðŸ”„ Verarbeite neues Dokument: {file_path.name}")
        
        # 1. Bildverarbeitung (Kantenerkennung, Perspektivkorrektur, Kontrast)
        logger.debug("  ðŸ“ Schritt 1: Bildverarbeitung...")
        processor = ImageProcessor()
        temp_dir = config.DATA_DIR / "temp"
        temp_dir.mkdir(exist_ok=True)
        processed_path = temp_dir / f"processed_{file_path.stem}.jpg"
        
        if not processor.process(file_path, processed_path):
            logger.error(f"  âŒ Bildverarbeitung fehlgeschlagen: {file_path.name}")
            return
        
        # 2. OCR-Texterkennung
        logger.debug("  Schritt 2: OCR-Texterkennung...")
        ocr = OCREngine()
        ocr_start = time.time()
        ocr_text = ocr.extract_text(processed_path)
        ocr_duration = int((time.time() - ocr_start) * 1000)
        
        if not ocr_text:
            logger.warning(f"  Kein Text erkannt in {file_path.name}")
            ocr_text = ""  # Leerer Text statt None
        
        # 3. PDF-Generierung mit OCR-Layer
        logger.debug("  ðŸ“„ Schritt 3: PDF-Generierung...")
        pdf_gen = PDFGenerator()
        initial_filename = f"{file_path.stem}.pdf"
        initial_pdf = config.DOCUMENTS_DIR / initial_filename
        
        if not pdf_gen.create_pdf_from_images([processed_path], initial_pdf, ocr_text):
            logger.error(f"  âŒ PDF-Erstellung fehlgeschlagen: {file_path.name}")
            return
        
        # 4. KI-Klassifikation
        logger.debug("  ðŸ¤– Schritt 4: KI-Klassifikation...")
        db = SessionLocal()
        category_name = None
        confidence = 0.0
        reasoning = ""
        
        try:
            # Lade verfÃ¼gbare Kategorien
            categories = db.query(Category).all()
            category_list = [
                {"name": cat.name, "description": cat.display_name}
                for cat in categories
            ]
            
            if category_list:
                classify_start = time.time()
                classification = await asyncio.to_thread(classifier.classify, ocr_text, category_list)
                classify_duration = int((time.time() - classify_start) * 1000)
                
                category_name = classification.get('category')
                confidence = classification.get('confidence', 0.0)
                reasoning = classification.get('reasoning', '')
                
                logger.info(f"    Klassifikation: {category_name} (Confidence: {confidence:.2f})")
                logger.debug(f"    Reasoning: {reasoning}")
            else:
                logger.warning("  âš ï¸ Keine Kategorien definiert - Ã¼berspringe Klassifikation")
        
        except Exception as e:
            logger.error(f"  âŒ Klassifikation fehlgeschlagen: {e}")
        
        # 5. KI-Namer (Semantic Filename)
        final_pdf = initial_pdf
        semantic_filename = None
        
        if category_name and classifier.should_auto_file(confidence):
            try:
                logger.debug("  Schritt 5: KI-Namer...")
                namer_start = time.time()
                semantic_filename = namer.generate_filename(
                    ocr_text, 
                    category_name, 
                    original_filename=file_path.name
                )
                namer_duration = int((time.time() - namer_start) * 1000)
                
                # Rename PDF
                new_pdf = config.DOCUMENTS_DIR / semantic_filename
                initial_pdf.rename(new_pdf)
                final_pdf = new_pdf
                
                logger.info(f"    Dateiname: {semantic_filename}")
            
            except Exception as e:
                logger.error(f"  Namer fehlgeschlagen: {e}")
                semantic_filename = initial_filename
        else:
            semantic_filename = initial_filename
        
        # 6. Auto-Filing (wenn Confidence >= Threshold)
        if category_name and classifier.should_auto_file(confidence):
            try:
                logger.debug("  Schritt 6: Auto-Filing...")
                file_start = time.time()
                filed_path = filer.file_document(
                    source_path=str(final_pdf),
                    category=category_name
                )
                file_duration = int((time.time() - file_start) * 1000)
                final_pdf = Path(filed_path)
                
                logger.info(f"    Abgelegt in: {final_pdf.parent}")
            
            except Exception as e:
                logger.error(f"  Auto-Filing fehlgeschlagen: {e}")
        
        # 7. Datenbank-Eintrag erstellen
        logger.debug("  ðŸ’¾ Schritt 7: Datenbank-Eintrag...")
        try:
            # Bestimme classification_status
            cls_status = "pending"
            if confidence and category_name:
                if classifier.should_auto_file(confidence):
                    cls_status = "auto_classified"
                else:
                    cls_status = "needs_user_help"

            doc = Document(
                filename=final_pdf.name,
                original_filename=file_path.name,
                file_path=str(final_pdf.relative_to(config.DATA_DIR)),
                file_size=final_pdf.stat().st_size,
                ocr_text=ocr_text[:50000] if ocr_text else None,
                page_count=1,
                processed=True,
                category_id=db.query(Category).filter(Category.name == category_name).first().id if category_name else None,
                classification_confidence=confidence,
                classification_reasoning=reasoning[:500] if reasoning else None,
                classification_status=cls_status
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            logger.success(f"âœ… Dokument verarbeitet: {final_pdf.name} (ID: {doc.id})")
            
            # 8. Feedback Store (wenn auto-confirmed)
            if classifier.should_auto_confirm(confidence):
                logger.debug("  ðŸ“š Schritt 8: Feedback Store (auto-confirm)...")
                feedback_store.add_feedback(
                    ocr_text=ocr_text[:2000],
                    category=category_name,
                    auto_confirmed=True,
                    confidence=confidence
                )
            
        except Exception as e:
            db.rollback()
            logger.error(f"  âŒ Datenbank-Fehler: {e}")
            raise
        finally:
            db.close()
        
        # 5. Cleanup: LÃ¶sche Original aus Inbox + Temp-Datei
        logger.debug("  ðŸ§¹ Schritt 5: Cleanup...")
        file_path.unlink(missing_ok=True)
        processed_path.unlink(missing_ok=True)
        
    except Exception as e:
        logger.error(f"âŒ Fehler bei Dokumentverarbeitung von {file_path.name}: {e}")
        import traceback
        logger.error(traceback.format_exc())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan Context Manager
    Startup: DB initialisieren, Hotfolder starten, USB Watcher starten
    Shutdown: Hotfolder stoppen, USB Watcher stoppen
    """
    global hotfolder_scanner
    
    # === STARTUP ===
    logger.info("VERA Office Backend startet...")
    
    # SSL-Zertifikate sicherstellen (generiert bei Bedarf)
    try:
        ensure_ssl_certs(config.BASE_DIR)
    except Exception as e:
        logger.warning(f"SSL certificate setup failed: {e} - HTTPS may not work")
    
    # Lizenz-Check beim Start
    license_ok = check_license_on_startup(config.DATA_DIR)
    if not license_ok:
        logger.error("âŒ Lizenz ungÃ¼ltig oder abgelaufen! Bitte kontaktieren Sie support@vera-office.de")
        # App startet trotzdem nicht â€” raise um zu stoppen
        # FÃ¼r Entwicklung: nur Warning
        logger.warning("âš ï¸ Starte trotzdem (Development-Modus)")
    
    # Diagnostics initialisieren
    diagnostics = init_diagnostics(None, config)
    
    # Datenbank initialisieren
    init_db()

    # Bug #1255 Fix: Kategorien beim Start seeden (idempotent) — ohne Kategorien HTTP 400 bei classify
    try:
        from backend.core.ai.template_knowledge import sync_categories_to_db
        from backend.db.database import SessionLocal
        _seed_db = SessionLocal()
        try:
            created = sync_categories_to_db(_seed_db)
            if created:
                logger.info(f"✅ {created} Kategorien aus YAML-Templates in DB angelegt")
            else:
                logger.info("✅ Kategorien bereits vorhanden (kein Seed nötig)")
        finally:
            _seed_db.close()
    except Exception as e:
        logger.warning(f"Kategorien-Seed fehlgeschlagen: {e} — classify-Endpunkt ggf. nicht nutzbar")

    # VERA Brain: DomÃ¤nenwissen seeden (nur wenn leer)
    from backend.core.ai.brain import brain
    if brain.get_stats()["domain_facts"] == 0:
        brain.seed_domain_knowledge()
        logger.info("ðŸ§  VERA Brain: DomÃ¤nenwissen initialisiert")
    
    # Hotfolder-Scanner starten (falls aktiviert)
    if config.HOTFOLDER_ENABLED:
        try:
            loop = asyncio.get_event_loop()
            hotfolder_scanner = HotfolderScanner(callback=process_new_document, loop=loop)
            hotfolder_scanner.start()
        except TypeError:
            # Ältere Version ohne loop-Argument
            hotfolder_scanner = HotfolderScanner(callback=process_new_document)
            hotfolder_scanner.start()
    
    # TEMPORARY DISABLED FOR BUG #10 DEBUG
    # mDNS Service registrieren
    # mdns_service.register(port=config.PORT, service_name="vera-office")
    logger.info("mDNS Service registration SKIPPED (DEBUG)")
    
    # Update-Client initialisieren und starten (prÃ¼ft periodisch auf Updates)
    config_dict = {
        "update_server": config.TELEMETRY_SERVER_URL.replace("/api/v1", "") if hasattr(config, "TELEMETRY_SERVER_URL") else "https://updates.vera-office.de",
        "license_key": "",  # TODO: Aus DB laden wenn vorhanden
        "version": config.APP_VERSION,
        "install_dir": str(config.BASE_DIR),
        "auto_update": True,
        "update_check_interval_hours": 24,
        "device_id": config.DEVICE_ID or ""
    }
    
    update_client = init_update_client(config_dict)
    await update_client.start()
    logger.info("✅ Update-Client gestartet")
    
    # Telemetrie-Client initialisieren und starten
    telemetry_config = {
        "update_server": config.TELEMETRY_SERVER_URL.replace("/api/v1", "") if hasattr(config, "TELEMETRY_SERVER_URL") else "https://updates.vera-office.de",
        "device_id": config.DEVICE_ID or "",
        "license_key": "",  # TODO: Aus DB laden
        "version": config.APP_VERSION,
        "telemetry": {
            "enabled": config.TELEMETRY_ENABLED if hasattr(config, "TELEMETRY_ENABLED") else True,
            "heartbeat_interval_minutes": config.TELEMETRY_HEARTBEAT_INTERVAL if hasattr(config, "TELEMETRY_HEARTBEAT_INTERVAL") else 30,
            "batch_size": config.TELEMETRY_BATCH_SIZE if hasattr(config, "TELEMETRY_BATCH_SIZE") else 50,
            "offline_buffer_max": config.TELEMETRY_OFFLINE_BUFFER_MAX if hasattr(config, "TELEMETRY_OFFLINE_BUFFER_MAX") else 1000
        }
    }
    
    # TEMPORARY DISABLED FOR BUG #10 DEBUG
    # telemetry_client = init_telemetry_client(telemetry_config)
    # await telemetry_client.start()
    logger.info("✅ Telemetrie-Client gestartet (DEAKTIVIERT - DEBUG)")
    
    # Telegram Bot starten (falls konfiguriert)
    try:
        from backend.services.telegram_bot import start_bot_background, load_token
        load_token()  # Wirft ValueError wenn kein Token
        start_bot_background()
        logger.info("✅ Telegram Bot gestartet")
    except ValueError:
        logger.info("Telegram Bot: kein Token konfiguriert — übersprungen")
    except ImportError as e:
        logger.warning(f"Telegram Bot: python-telegram-bot nicht installiert — {e}")
    except Exception as e:
        logger.warning(f"Telegram Bot konnte nicht gestartet werden: {e}")

    # Lehrbuch-Scheduler starten (Bug #59 Fix)
    try:
        from backend.services.lehrbuch_scheduler import start_lehrbuch_scheduler
        vera_db = config.DATA_DIR / "vera.db"
        brain_db = config.DATA_DIR / "vera_brain.db"
        asyncio.create_task(start_lehrbuch_scheduler(vera_db, brain_db))
        logger.info("✅ Lehrbuch-Scheduler gestartet (24h Intervall)")
    except Exception as e:
        logger.warning(f"Lehrbuch-Scheduler konnte nicht gestartet werden: {e}")

    logger.success(f"VERA Office Backend bereit auf {config.HOST}:{config.PORT}")

    # httpx AsyncClient für Chat-Endpoints (Bug #1189)
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(120.0, connect=10.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
    )
    logger.success("✅ HTTP Client (shared) initialisiert")

    yield  # App läuft

    # === SHUTDOWN ===
    logger.info("VERA Office Backend stoppt...")

    # Telegram Bot stoppen
    try:
        from backend.services.telegram_bot import stop_bot
        stop_bot()
    except Exception:
        pass
    
    if hotfolder_scanner:
        hotfolder_scanner.stop()
    
    # httpx AsyncClient schließen (Bug #1189)
    if hasattr(app.state, 'http_client'):
        await app.state.http_client.aclose()
    
    # Update-Client stoppen
    update_client = get_update_client()
    if update_client:
        await update_client.stop()
    
    # Telemetrie-Client stoppen
    telemetry_client = get_telemetry_client()
    if telemetry_client:
        await telemetry_client.stop()
    
    # mDNS Service deregistrieren
    mdns_service.unregister()
    
    logger.success("Shutdown abgeschlossen")


# FastAPI App
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="On-Premise Dokumenten-Agent fÃ¼r KMU",
    lifespan=lifespan,
    docs_url="/api/docs" if config.DEBUG else None,  # Swagger UI nur im Debug-Modus
    redoc_url="/api/redoc" if config.DEBUG else None
)

# CORS Middleware (erlaubt Frontend-Zugriff)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Middleware (JWT Token Verification fÃ¼r geschÃ¼tzte Routen)
app.add_middleware(AuthMiddleware)

# Modul-System initialisieren (Registry, Lizenzierung, Middleware)
try:
    module_registry = setup_modules(app)
    logger.info(f"Modul-System geladen: {len(module_registry.all_modules())} Module")
except FileNotFoundError as e:
    logger.error(f"Modul-System konnte nicht geladen werden: {e}")
    logger.warning("âš ï¸ VERA lÃ¤uft ohne Modul-System (nur Basis-Features)")
except Exception as e:
    logger.error(f"Modul-System Fehler: {e}")
    logger.warning("âš ï¸ VERA lÃ¤uft ohne Modul-System (nur Basis-Features)")

# API Routers einbinden
app.include_router(auth.router)        # Auth Router (kein Prefix - hat eigenen /api/auth)
app.include_router(auth.setup_router)  # Setup Router (/api/setup)
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(onboarding_admin.router)  # Admin-User-Erstellung (eigener Prefix)
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
# documents_download.router entfernt: duplicate GET /{document_id}/download — documents.router:533 ist aktiv
app.include_router(documents_ai.router, prefix="/api/documents", tags=["Documents AI"])
app.include_router(agent.router, prefix="/api", tags=["Agent"])
app.include_router(scanner.router)
app.include_router(folders.router, prefix="/api/folders", tags=["Folders"])
app.include_router(discovery.router, prefix="/api/system", tags=["Discovery"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(promo.router, prefix="/api", tags=["Promo"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(workflow.router, prefix="/api", tags=["Workflow"])
app.include_router(vera_chat.router)  # Bug #1189: /api/chat/messages (prefix im Router: /api/chat)
app.include_router(ocr.router)  # /api/ocr/jobs + /api/ocr/upload
app.include_router(dms.router, prefix="/api/dms", tags=["DMS"])  # /api/dms/files
app.include_router(settings.router, prefix="/api", tags=["Settings"])  # /api/settings
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])  # /api/calendar/events

# Bug #1252: /api/qm/* Alias — QM router ist nur unter /api/modules/qm/ gemountet,
# aber auth_middleware schützt /api/qm/ und Frontend + QA testen dort.
# Fix: QM router zusätzlich unter /api/qm/ einbinden (Auth via Middleware, nicht Depends).
try:
    from backend.modules.qm.router import router as qm_router_alias
    app.include_router(qm_router_alias, prefix="/api/qm", tags=["QM"])  # /api/qm/dashboard etc.
    logger.info("QM Router zusätzlich unter /api/qm/ gemountet (Bug #1252 Fix)")
except ImportError as e:
    logger.warning(f"QM Router Alias konnte nicht gemountet werden: {e}")


# Frontend dist path
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Health Check
@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "healthy", "version": config.APP_VERSION}

# Frontend SPA serving
# Mount assets first, then handle SPA routing
if FRONTEND_DIST.exists():
    # Static assets
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    # Root-level static files (logo, icons, manifest)
    for static_file in ["vera-logo.svg", "vera-logo.png", "vera-icon.svg", "manifest.json", "favicon.svg", "favicon.png", "vite.svg", "favicon.ico"]:
        _path = FRONTEND_DIST / static_file
        if _path.exists():
            _f = _path  # capture for closure
            app.add_api_route(f"/{static_file}", lambda f=_f: FileResponse(f), methods=["GET"], include_in_schema=False)
    
    # Serve index.html for root and SPA routes
    # This does NOT use a catch-all pattern to avoid interfering with API routes
    @app.get("/")
    async def root():
        return FileResponse(FRONTEND_DIST / "index.html")
    
    # Define explicit SPA routes
    spa_routes = ["/chat", "/documents", "/capture", "/search", "/tasks", "/export", "/settings", "/onboarding", "/qm", "/erp", "/login", "/recent", "/dashboard", "/finanzen", "/inbox"]
    
    def create_spa_handler(route_path):
        async def handler():
            return FileResponse(FRONTEND_DIST / "index.html")
        return handler
    
    for route in spa_routes:
        app.add_api_route(route, create_spa_handler(route), methods=["GET"], include_in_schema=False)
    
    # For document detail routes with parameters
    @app.get("/documents/{path:path}")
    async def documents_spa(path: str):
        return FileResponse(FRONTEND_DIST / "index.html")

    # Bug #690/#689 fix: QM and ERP sub-routes as SPA routes
    @app.get("/qm/{path:path}")
    async def qm_spa(path: str):
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/finanzen/{path:path}")
    async def finanzen_spa(path: str):
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="debug" if config.DEBUG else "info"
    )

