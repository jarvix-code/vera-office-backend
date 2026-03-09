"""
VERA Office - Documents API
Upload, Liste, Abruf, Suche von Dokumenten
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import shutil

from backend.db.database import get_db
from backend.models.document import Document
from backend.models.category import Category
from backend.core.image_processor import ImageProcessor
from backend.core.ocr_engine import OCREngine
from backend.core.pdf_generator import PDFGenerator
from backend.core.quality_checker import QualityChecker
from backend.core.ai.classifier import classifier
from backend.core.ai.namer import namer
from backend.core.ai.filer import filer
from backend.core.ai.feedback_store import feedback_store
from backend.core.ai.vision_checker import vision_checker
from backend.core.ai.template_knowledge import sync_categories_to_db
from backend.core.folder_manager import folder_manager
from backend.config import config
from loguru import logger

router = APIRouter()


# Response Models
class DocumentResponse(BaseModel):
    """Dokument-Response"""
    id: int
    filename: str
    original_filename: Optional[str]
    file_size: int
    category_id: Optional[int]
    category_name: Optional[str]
    classification_confidence: Optional[float]
    ocr_text: Optional[str]
    document_date: Optional[datetime]
    sender: Optional[str]
    reference_number: Optional[str]
    amount: Optional[float]
    page_count: int
    processed: bool
    quality_score: Optional[float] = None
    quality_issues: Optional[List[str]] = None
    original_image_path: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompareResponse(BaseModel):
    """Vergleichs-Response für Frontend"""
    document_id: int
    original_image_url: Optional[str]
    pdf_url: Optional[str]
    quality_score: Optional[float]
    quality_issues: List[str] = []
    ocr_text: Optional[str]
    status: str  # processed, needs_review, needs_rescan


class DocumentListResponse(BaseModel):
    """Listen-Response"""
    total: int
    items: List[DocumentResponse]


class UploadResponse(BaseModel):
    """Upload-Response"""
    success: bool
    document_id: Optional[int]
    message: str
    duplicate: bool = False


# Hilfsfunktionen
def _build_doc_response(doc, ocr_preview: bool = False) -> DocumentResponse:
    """Baut DocumentResponse aus DB-Objekt."""
    category_name = doc.category.display_name if doc.category else None
    ocr_text = doc.ocr_text
    if ocr_preview and ocr_text:
        ocr_text = ocr_text[:500]
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        category_id=doc.category_id,
        category_name=category_name,
        classification_confidence=doc.classification_confidence,
        ocr_text=ocr_text,
        document_date=doc.document_date,
        sender=doc.sender,
        reference_number=doc.reference_number,
        amount=doc.amount,
        page_count=doc.page_count,
        processed=doc.processed,
        quality_score=doc.quality_score,
        quality_issues=QualityChecker.issues_from_json(doc.quality_issues),
        original_image_path=doc.original_image_path,
        created_at=doc.created_at,
    )


def calculate_file_hash(file_path: Path) -> str:
    """
    Berechnet SHA256-Hash einer Datei (für Duplikaterkennung)
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


async def process_document_pipeline(file_path: Path, original_filename: str, db: Session) -> Document:
    """
    Vollständige Dokumentenverarbeitungs-Pipeline
    1. Bildverarbeitung
    2. OCR
    3. PDF-Generierung
    4. Klassifikation (TODO)
    5. DB-Eintrag
    """
    logger.info(f"🔄 Verarbeite Dokument: {original_filename}")
    
    # Initialisiere Prozessoren
    image_processor = ImageProcessor()
    ocr_engine = OCREngine()
    pdf_generator = PDFGenerator()
    quality_checker = QualityChecker()
    
    # Dateityp prüfen
    file_ext = file_path.suffix.lower()
    
    # Verarbeitungs-Pfade
    processed_image_path = config.DATA_DIR / "temp" / f"processed_{file_path.stem}.jpg"
    processed_image_path.parent.mkdir(parents=True, exist_ok=True)
    
    ocr_text = None
    final_path = None
    original_image_path = None
    
    try:
        if file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            # Originalbild aufbewahren
            originals_dir = config.DATA_DIR / "originals"
            originals_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_image_path = originals_dir / f"{timestamp}_{file_path.name}"
            shutil.copy2(file_path, original_image_path)
            logger.info(f"  💾 Original gespeichert: {original_image_path.name}")
            
            # Bildverarbeitung
            logger.info("  📸 Starte Bildverarbeitung...")
            success = image_processor.process(file_path, processed_image_path)
            
            if not success:
                logger.warning("  ⚠️ Bildverarbeitung fehlgeschlagen, nutze Original")
                processed_image_path = file_path
            
            # OCR
            logger.info("  📝 Starte OCR...")
            ocr_text = ocr_engine.extract_text(processed_image_path)
            
            # PDF generieren
            pdf_filename = f"{timestamp}_{file_path.stem}.pdf"
            final_path = config.DOCUMENTS_DIR / pdf_filename
            
            logger.info("  📄 Generiere PDF...")
            pdf_generator.create_pdf_from_images(
                image_paths=[processed_image_path],
                output_path=final_path,
                ocr_text=ocr_text
            )
            
        elif file_ext == '.pdf':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"{timestamp}_{file_path.stem}.pdf"
            final_path = config.DOCUMENTS_DIR / pdf_filename
            
            shutil.copy2(file_path, final_path)
            logger.info(f"  📄 PDF kopiert: {pdf_filename}")
            
        else:
            raise ValueError(f"Nicht unterstützter Dateityp: {file_ext}")
        
        # Qualitätsprüfung (Heuristik)
        quality_score = None
        quality_issues_json = None
        quality_issues = []
        status_flag = True  # processed by default
        
        if original_image_path and original_image_path.exists():
            quality_score, quality_issues = quality_checker.check(original_image_path, ocr_text)
            
            # Vision-LLM Qualitätsprüfung (ergänzt Heuristik)
            try:
                vision_result = vision_checker.check_quality(str(original_image_path))
                if vision_result.get('available') and vision_result.get('quality_score') is not None:
                    vision_score = vision_result['quality_score']
                    # Combine: average of heuristic and vision scores
                    if quality_score is not None:
                        quality_score = (quality_score + vision_score) / 2.0
                    else:
                        quality_score = vision_score
                    # Add vision issues
                    quality_issues.extend(vision_result.get('issues', []))
                    if vision_result.get('suggestion') and vision_result['suggestion'] != 'Gute Qualität':
                        quality_issues.append(f"Vision: {vision_result['suggestion']}")
                    logger.info(f"  👁️ Vision-Check: Score={vision_score:.2f}, Issues={vision_result.get('issues', [])}")
            except Exception as e:
                logger.warning(f"  ⚠️ Vision-Check fehlgeschlagen: {e}")
            
            quality_issues_json = QualityChecker.issues_to_json(quality_issues)
            doc_status = QualityChecker.determine_status(quality_score)
            
            if doc_status == "needs_review":
                logger.warning(f"  ⚠️ Qualität fragwürdig (Score: {quality_score}) - needs_review")
                status_flag = False
            elif doc_status == "needs_rescan":
                logger.warning(f"  ❌ Qualität schlecht (Score: {quality_score}) - needs_rescan")
                status_flag = False
        
        # Datei-Hash berechnen (Duplikaterkennung)
        file_hash = calculate_file_hash(final_path)
        file_size = final_path.stat().st_size
        
        # === AI CLASSIFICATION ===
        category_id = None
        classification_confidence = None
        classification_reasoning = None
        ai_filename = None
        
        if ocr_text and len(ocr_text.strip()) > 20:
            try:
                # Sync categories from YAML to DB (idempotent)
                sync_categories_to_db(db)
                
                # Classify
                logger.info("  🤖 Starte KI-Klassifizierung...")
                result = classifier.classify(ocr_text)
                classification_confidence = result['confidence']
                classification_reasoning = result.get('reasoning', '')[:500]
                
                logger.info(f"  🏷️ Kategorie: {result['category']} (Confidence: {classification_confidence:.0%})")
                
                if result['category'] != 'unknown':
                    # Find or create category in DB
                    category = db.query(Category).filter(Category.name == result['category']).first()
                    if category:
                        category_id = category.id
                    
                    # Auto-name using LLM
                    ai_filename = namer.generate_filename(ocr_text, result['category'], original_filename)
                    logger.info(f"  📝 KI-Dateiname: {ai_filename}")
                    
                    # Auto-file if confidence >= threshold
                    if classifier.should_auto_file(classification_confidence):
                        try:
                            target_folder = folder_manager.ensure_folder(
                                result['category'],
                                metadata={'date': datetime.now()}
                            )
                            if target_folder:
                                target_path = Path(target_folder) / ai_filename
                                if target_path.exists():
                                    # Avoid overwrite
                                    stem = target_path.stem
                                    suffix = target_path.suffix
                                    counter = 1
                                    while target_path.exists():
                                        target_path = Path(target_folder) / f"{stem}_{counter}{suffix}"
                                        counter += 1
                                
                                shutil.move(str(final_path), str(target_path))
                                final_path = target_path
                                logger.info(f"  📁 Auto-Filed: {target_path}")
                                
                                # Add to feedback store (auto-confirmed)
                                if classifier.should_auto_confirm(classification_confidence):
                                    feedback_store.add_feedback(
                                        ocr_text=ocr_text[:2000],
                                        category=result['category'],
                                        auto_confirmed=True,
                                        confidence=classification_confidence
                                    )
                        except Exception as e:
                            logger.warning(f"  ⚠️ Auto-Filing fehlgeschlagen: {e}")
                    else:
                        logger.info(f"  ℹ️ Confidence {classification_confidence:.0%} < Threshold — User muss bestätigen")
                
            except Exception as e:
                logger.warning(f"  ⚠️ KI-Klassifizierung fehlgeschlagen: {e}")
        
        # Dokument in DB erstellen
        document = Document(
            filename=ai_filename or final_path.name,
            original_filename=original_filename,
            file_path=str(final_path),
            file_size=file_size,
            file_hash=file_hash,
            ocr_text=ocr_text,
            ocr_language=config.OCR_LANGUAGE,
            category_id=category_id,
            classification_confidence=classification_confidence,
            page_count=1,
            processed=status_flag,
            original_image_path=str(original_image_path) if original_image_path else None,
            quality_score=quality_score,
            quality_issues=quality_issues_json,
            created_at=datetime.utcnow()
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.success(f"✅ Dokument verarbeitet: {document.filename} (ID: {document.id}, Quality: {quality_score})")
        
        # Cleanup temp
        if processed_image_path != file_path and processed_image_path.exists():
            processed_image_path.unlink()
        
        return document
        
    except Exception as e:
        logger.error(f"❌ Fehler bei Dokumentenverarbeitung: {e}")
        raise


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Lädt ein neues Dokument hoch und verarbeitet es
    """
    try:
        # Validierung
        if not file.filename:
            raise HTTPException(status_code=400, detail="Kein Dateiname")
        
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Nicht unterstützter Dateityp: {file_ext}. Erlaubt: {', '.join(allowed_extensions)}"
            )
        
        # Temporäre Datei speichern
        temp_path = config.INBOX_DIR / file.filename
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"📥 Datei hochgeladen: {file.filename} ({temp_path.stat().st_size} bytes)")
        
        # Duplikat-Check (optional)
        file_hash = calculate_file_hash(temp_path)
        existing = db.query(Document).filter(Document.file_hash == file_hash).first()
        
        if existing:
            temp_path.unlink()  # Temporäre Datei löschen
            logger.warning(f"⚠️ Duplikat erkannt: {file.filename} (bereits vorhanden als {existing.filename})")
            return UploadResponse(
                success=False,
                document_id=existing.id,
                message=f"Dokument bereits vorhanden: {existing.filename}",
                duplicate=True
            )
        
        # Verarbeitung
        document = await process_document_pipeline(temp_path, file.filename, db)
        
        # Temporäre Datei löschen
        if temp_path.exists():
            temp_path.unlink()
        
        return UploadResponse(
            success=True,
            document_id=document.id,
            message="Dokument erfolgreich hochgeladen und verarbeitet"
        )
        
    except Exception as e:
        logger.error(f"❌ Upload-Fehler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Listet Dokumente auf (mit Pagination, Filter, Suche)
    """
    query = db.query(Document).filter(Document.deleted == False)
    
    # Filter nach Kategorie
    if category_id:
        query = query.filter(Document.category_id == category_id)
    
    # Volltextsuche
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Document.filename.ilike(search_term),
                Document.ocr_text.ilike(search_term),
                Document.sender.ilike(search_term),
                Document.reference_number.ilike(search_term)
            )
        )
    
    # Total Count
    total = query.count()
    
    # Pagination
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    # Response aufbauen
    items = [_build_doc_response(doc, ocr_preview=True) for doc in documents]
    
    return DocumentListResponse(total=total, items=items)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Holt ein einzelnes Dokument nach ID
    """
    document = db.query(Document).filter(
        and_(Document.id == document_id, Document.deleted == False)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    return _build_doc_response(document)


@router.get("/{document_id}/download")
async def download_document(document_id: int, db: Session = Depends(get_db)):
    """
    Lädt die PDF-Datei herunter
    """
    document = db.query(Document).filter(
        and_(Document.id == document_id, Document.deleted == False)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    file_path = Path(document.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    
    return FileResponse(
        path=file_path,
        filename=document.filename,
        media_type="application/pdf"
    )


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Löscht ein Dokument (Soft Delete)
    """
    document = db.query(Document).filter(
        and_(Document.id == document_id, Document.deleted == False)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    # Soft Delete
    document.deleted = True
    document.deleted_at = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"🗑️ Dokument gelöscht: {document.filename} (ID: {document.id})")
    
    return {"status": "ok", "message": "Dokument gelöscht"}


@router.get("/search/query")
async def search_documents(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Natürliche Sprachsuche (Volltextsuche im OCR-Text)
    """
    search_term = f"%{q}%"
    
    documents = db.query(Document).filter(
        and_(
            Document.deleted == False,
            or_(
                Document.ocr_text.ilike(search_term),
                Document.filename.ilike(search_term),
                Document.sender.ilike(search_term),
                Document.reference_number.ilike(search_term)
            )
        )
    ).order_by(Document.created_at.desc()).limit(limit).all()
    
    results = [_build_doc_response(doc, ocr_preview=True) for doc in documents]
    
    return {"query": q, "total": len(results), "results": results}


@router.get("/{document_id}/compare", response_model=CompareResponse)
async def compare_document(document_id: int, db: Session = Depends(get_db)):
    """
    Vergleichs-Endpunkt: Original-Bild + PDF + Quality-Score
    Für Frontend-Vergleichsview
    """
    document = db.query(Document).filter(
        and_(Document.id == document_id, Document.deleted == False)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    # URLs für Frontend
    original_url = None
    if document.original_image_path and Path(document.original_image_path).exists():
        original_url = f"/api/documents/{document_id}/original"
    
    pdf_url = f"/api/documents/{document_id}/download"
    
    quality_issues = QualityChecker.issues_from_json(document.quality_issues)
    score = document.quality_score or 0
    status = QualityChecker.determine_status(score)
    
    return CompareResponse(
        document_id=document.id,
        original_image_url=original_url,
        pdf_url=pdf_url,
        quality_score=document.quality_score,
        quality_issues=quality_issues,
        ocr_text=document.ocr_text,
        status=status,
    )


@router.get("/{document_id}/original")
async def get_original_image(document_id: int, db: Session = Depends(get_db)):
    """
    Gibt das Originalbild zurück
    """
    document = db.query(Document).filter(
        and_(Document.id == document_id, Document.deleted == False)
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    
    if not document.original_image_path:
        raise HTTPException(status_code=404, detail="Kein Originalbild vorhanden")
    
    original_path = Path(document.original_image_path)
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="Originalbild-Datei nicht gefunden")
    
    return FileResponse(
        path=original_path,
        filename=original_path.name,
        media_type=f"image/{original_path.suffix.lstrip('.').replace('jpg', 'jpeg')}"
    )
