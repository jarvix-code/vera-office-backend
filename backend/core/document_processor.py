"""
VERA Office - Unified Document Processor
Verarbeitet Bilder UND PDFs → Text in DB

Pipeline:
1. Bild (JPG/PNG) → OCR → Durchsuchbares PDF → Text in DB
2. PDF (OCR-lesbar) → Text extrahieren → Text in DB  
3. PDF (nicht OCR-lesbar) → OCR → Text in DB
"""
from pathlib import Path
from typing import Tuple, Optional, List
from loguru import logger

from backend.config import config
from backend.core.image_processor import ImageProcessor
from backend.core.ocr_engine import OCREngine
from backend.core.pdf_generator import PDFGenerator
from backend.core.pdf_processor import PDFProcessor
from backend.models.document import Document
from backend.models.category import Category
from backend.db.database import SessionLocal


class DocumentProcessor:
    """
    Unified Processor für Bilder + PDFs
    """
    
    def __init__(self):
        self.image_processor = ImageProcessor()
        self.ocr_engine = OCREngine()
        self.pdf_generator = PDFGenerator()
        self.pdf_processor = PDFProcessor()
        
        # Supported formats
        self.image_formats = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        self.pdf_format = {'.pdf'}
        
    async def process_document(self, file_path: Path) -> Optional[Document]:
        """
        Verarbeitet Bild ODER PDF → Text in DB
        
        Args:
            file_path: Pfad zur Input-Datei (Bild oder PDF)
            
        Returns:
            Document-Objekt (in DB gespeichert) oder None bei Fehler
        """
        try:
            logger.info(f"📄 [UNIFIED] Verarbeite: {file_path.name}")
            
            file_ext = file_path.suffix.lower()
            
            # Route 1: BILD → OCR → PDF → DB
            if file_ext in self.image_formats:
                return await self._process_image(file_path)
            
            # Route 2+3: PDF → Text extrahieren ODER OCR → DB
            elif file_ext in self.pdf_format:
                return await self._process_pdf(file_path)
            
            else:
                logger.warning(f"  ⏭ Nicht unterstütztes Format: {file_ext}")
                return None
                
        except Exception as e:
            logger.error(f"[ERROR] Document Processing fehlgeschlagen: {e}")
            return None
    
    async def _process_image(self, image_path: Path) -> Optional[Document]:
        """
        Route 1: Bild → OCR → Durchsuchbares PDF → Text in DB
        
        Pipeline:
        1. Bildverarbeitung (Kantenerkennung, Perspektivkorrektur)
        2. OCR auf Bild
        3. Erstelle durchsuchbares PDF mit OCR-Layer
        4. Archiviere PDF
        5. Speichere Text in DB
        """
        try:
            logger.debug("  🖼 [IMAGE] Route 1: Bild → OCR → PDF → DB")
            
            # 1. Bildverarbeitung
            temp_dir = config.DATA_DIR / "temp"
            temp_dir.mkdir(exist_ok=True)
            processed_path = temp_dir / f"processed_{image_path.stem}.jpg"
            
            if not self.image_processor.process(image_path, processed_path):
                logger.error(f"  ❌ Bildverarbeitung fehlgeschlagen: {image_path.name}")
                return None
            
            # 2. OCR auf Bild
            logger.debug("  🔍 OCR auf Bild...")
            ocr_text = self.ocr_engine.extract_text(processed_path)
            
            if not ocr_text or len(ocr_text.strip()) < 10:
                logger.warning(f"  ⚠️ Kein Text erkannt in {image_path.name}")
                ocr_text = ""
            
            logger.debug(f"    ✓ {len(ocr_text)} Zeichen erkannt")
            
            # 3. Erstelle durchsuchbares PDF
            logger.debug("  📄 Erstelle durchsuchbares PDF...")
            pdf_filename = f"{image_path.stem}.pdf"
            pdf_path = config.DOCUMENTS_DIR / pdf_filename
            
            if not self.pdf_generator.create_pdf_from_images([processed_path], pdf_path, ocr_text):
                logger.error(f"  ❌ PDF-Erstellung fehlgeschlagen")
                return None
            
            # 4. Cleanup temp files
            processed_path.unlink(missing_ok=True)
            
            # 5. Speichere in DB
            return await self._save_to_db(
                original_filename=image_path.name,
                pdf_path=pdf_path,
                ocr_text=ocr_text,
                page_count=1
            )
            
        except Exception as e:
            logger.error(f"[ERROR] Image Processing fehlgeschlagen: {e}")
            return None
    
    async def _process_pdf(self, pdf_path: Path) -> Optional[Document]:
        """
        Route 2+3: PDF → Text extrahieren ODER OCR → DB
        
        Pipeline:
        - Öffne PDF einmalig
        - Prüfe: Hat PDF bereits Text? (>50 Zeichen)
        - JA → Route 2: Extrahiere Text → DB
        - NEIN → Route 3: OCR auf PDF-Seiten → DB
        """
        try:
            logger.debug("  📕 [PDF] Route 2/3: PDF → Text/OCR → DB")
            
            # Öffne PDF EINMALIG und prüfe + extrahiere in einem Durchlauf
            import fitz
            doc = fitz.open(str(pdf_path))
            
            # Extrahiere Text von allen Seiten
            text_parts = []
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_parts.append(text)
            
            page_count = doc.page_count
            doc.close()
            
            ocr_text = "\n\n".join(text_parts).strip()
            
            # Check: Hat PDF genug Text? (>50 Zeichen)
            if len(ocr_text) > 50:
                # Route 2: Text extrahiert
                logger.debug(f"  ✓ PDF hat bereits Text → {len(ocr_text)} Zeichen extrahiert")
            else:
                # Route 3: OCR auf PDF
                logger.debug("  🔍 PDF hat keinen Text → OCR")
                ocr_text, temp_images = self.pdf_processor.ocr_pdf(pdf_path)
                
                # Cleanup temp images
                for temp_img in temp_images:
                    temp_img.unlink(missing_ok=True)
            
            if not ocr_text or len(ocr_text.strip()) < 10:
                logger.warning(f"  ⚠️ Kein Text im PDF: {pdf_path.name}")
                ocr_text = ""
            
            logger.debug(f"    ✓ {len(ocr_text)} Zeichen gesamt")
            
            # Archiviere PDF (copy to documents dir if not already there)
            if pdf_path.parent != config.DOCUMENTS_DIR:
                final_pdf = config.DOCUMENTS_DIR / pdf_path.name
                
                # Check if file already exists (skip if yes)
                if final_pdf.exists():
                    logger.warning(f"  ⚠️ Datei existiert bereits: {final_pdf.name}")
                    return None
                
                import shutil
                shutil.copy(str(pdf_path), str(final_pdf))
                pdf_path = final_pdf
            
            # Speichere in DB
            return await self._save_to_db(
                original_filename=pdf_path.name,
                pdf_path=pdf_path,
                ocr_text=ocr_text,
                page_count=page_count
            )
            
        except Exception as e:
            logger.error(f"[ERROR] PDF Processing fehlgeschlagen: {e}")
            return None
    
    async def _save_to_db(
        self,
        original_filename: str,
        pdf_path: Path,
        ocr_text: str,
        page_count: int
    ) -> Optional[Document]:
        """
        Speichert Dokument in DB (mit OCR-Text!)
        
        Args:
            original_filename: Original-Dateiname
            pdf_path: Pfad zum archivierten PDF
            ocr_text: OCR-Text (WICHTIG!)
            page_count: Anzahl Seiten
            
        Returns:
            Document-Objekt oder None bei Fehler
        """
        db = SessionLocal()
        try:
            logger.debug("  💾 Speichere in DB...")
            
            # Klassifikation (optional, kann auch später passieren)
            # Hier nur DB-Eintrag, Klassifikation macht die Pipeline in main.py
            
            doc = Document(
                filename=pdf_path.name,
                original_filename=original_filename,
                file_path=str(pdf_path.relative_to(config.DATA_DIR)),
                file_size=pdf_path.stat().st_size,
                ocr_text=ocr_text[:50000] if ocr_text else None,  # Truncate at 50k chars
                page_count=page_count,
                processed=False,  # Klassifikation noch nicht gelaufen
            )
            
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            logger.success(f"  ✅ Dokument in DB: ID {doc.id} ({len(ocr_text)} Zeichen OCR-Text)")
            
            return doc
            
        except Exception as e:
            db.rollback()
            logger.error(f"[ERROR] DB-Speicherung fehlgeschlagen: {e}")
            return None
        finally:
            db.close()
