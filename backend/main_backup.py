"""
VERA Office - FastAPI Backend
Hauptapplikation mit Lifespan, CORS, Health-Endpoints
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger
import sys

from backend.config import config
from backend.db.database import init_db
from backend.core.scanner import HotfolderScanner
from backend.core.mdns import mdns_service
from backend.core.ssl_setup import ensure_ssl_certs
from backend.core.diagnostics import init_diagnostics, get_diagnostics
from backend.core.license_check import check_license_on_startup
from backend.core.auth_middleware import AuthMiddleware
from backend.modules.setup import setup_modules
from backend.api import documents, documents_ai, documents_download, onboarding, onboarding_admin, system, scanner, agent, folders, auth
from backend.api import discovery, feedback, qm_tools, duplicate_api, vera_tools, qm_ocr, usb_import, inbox_processor
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
        
        # 2.5. DUPLIKAT-CHECK (NEU!)
        logger.debug("  [SEARCH] Schritt 2.5: Duplikat-Prüfung...")
        from backend.core.duplicate_handler import check_duplicate, create_pending_duplicate, get_duplicate_notification
        
        db = SessionLocal()
        duplicate_doc = check_duplicate(ocr_text, db)
        
        if duplicate_doc:
            logger.warning(f"  [WARNING] DUPLIKAT ERKANNT!")
            logger.warning(f"      Existierendes Dokument: {duplicate_doc.filename} (ID {duplicate_doc.id})")
            
            # Create confirmation request
            confirmation_id = create_pending_duplicate(file_path, ocr_text, duplicate_doc)
            notification = get_duplicate_notification(duplicate_doc)
            
            # TODO: Send notification to VERA Chat
            # For now: Create a system message that VERA will see
            logger.warning(f"  Benachrichtigung erstellt: {confirmation_id}")
            logger.warning(f"      {notification['message']}")
            
            # Move file to pending folder instead of deleting
            pending_dir = config.DATA_DIR / "pending_duplicates"
            pending_dir.mkdir(exist_ok=True)
            pending_file = pending_dir / f"{confirmation_id}_{file_path.name}"
            
            import shutil
            shutil.move(str(file_path), str(pending_file))
            processed_path.unlink(missing_ok=True)
            
            logger.info(f"  [PAUSE]  Dokument pausiert - warte auf User-Entscheidung")
            return  # STOP processing until user confirms!
        
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
                classification = classifier.classify(ocr_text, category_list)
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
                classification_reasoning=reasoning[:500] if reasoning else None
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

