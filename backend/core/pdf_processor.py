"""
VERA Office - PDF Processor
Verarbeitet PDFs: Text-Extraktion, OCR-Check, OCR auf PDF-Seiten
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple
from loguru import logger
from backend.config import config


class PDFProcessor:
    """
    PDF-Verarbeitung: Text-Extraktion und OCR-Bedarf-Prüfung
    """
    
    def __init__(self):
        self.min_text_length = 50  # Minimum Zeichen für "hat OCR-Text"
        
    def has_ocr_text(self, pdf_path: Path) -> bool:
        """
        Prüft ob PDF bereits OCR-Text enthält
        
        Args:
            pdf_path: Pfad zum PDF
            
        Returns:
            True wenn PDF bereits Text enthält (>50 Zeichen)
        """
        try:
            doc = fitz.open(str(pdf_path))
            total_text = ""
            
            # Prüfe alle Seiten
            for page_num in range(min(doc.page_count, 5)):  # Max 5 Seiten prüfen
                page = doc.load_page(page_num)
                text = page.get_text()
                total_text += text
                
                # Early exit wenn genug Text gefunden
                if len(total_text.strip()) > self.min_text_length:
                    has_text = True
                    text_len = len(total_text)
                    doc.close()
                    logger.debug(f"  [PDF] Hat bereits Text: {text_len} Zeichen")
                    return has_text
            
            has_text = len(total_text.strip()) > self.min_text_length
            if not has_text:
                logger.debug(f"  [PDF] Kein Text gefunden ({len(total_text)} Zeichen)")
            
            doc.close()
            return has_text
            
        except Exception as e:
            logger.error(f"[ERROR] PDF Text-Check fehlgeschlagen: {e}")
            return False
    
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrahiert Text aus PDF (alle Seiten)
        
        Args:
            pdf_path: Pfad zum PDF
            
        Returns:
            Extrahierter Text (oder leerer String bei Fehler)
        """
        try:
            doc = fitz.open(str(pdf_path))
            text_parts = []
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_parts.append(text)
            
            doc.close()
            
            full_text = "\n\n".join(text_parts)
            logger.debug(f"  [PDF] Text extrahiert: {len(full_text)} Zeichen ({doc.page_count} Seiten)")
            
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"[ERROR] PDF Text-Extraktion fehlgeschlagen: {e}")
            return ""
    
    def ocr_pdf(self, pdf_path: Path) -> Tuple[str, List[Path]]:
        """
        Führt OCR auf PDF durch (konvertiert Seiten zu Bildern → OCR)
        
        Args:
            pdf_path: Pfad zum PDF
            
        Returns:
            Tuple (ocr_text, image_paths) - Text und Liste der generierten Bilder
        """
        from backend.core.ocr_engine import OCREngine
        import tempfile
        
        try:
            logger.info(f"  [PDF-OCR] Starte OCR auf PDF: {pdf_path.name}")
            
            doc = fitz.open(str(pdf_path))
            ocr_engine = OCREngine()
            
            text_parts = []
            image_paths = []
            
            # Erstelle temp dir für PDF-Page-Images
            temp_dir = config.DATA_DIR / "temp" / "pdf_pages"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # Konvertiere PDF-Seite zu Bild (300 DPI für gute OCR-Qualität)
                pix = page.get_pixmap(dpi=300)
                
                # Speichere als temporäres Bild
                temp_image = temp_dir / f"page_{page_num + 1}_{pdf_path.stem}.png"
                pix.save(str(temp_image))
                image_paths.append(temp_image)
                
                # OCR auf Bild
                page_text = ocr_engine.extract_text(temp_image)
                text_parts.append(page_text)
                
                logger.debug(f"    [OK] Seite {page_num + 1}/{doc.page_count}: {len(page_text)} Zeichen")
            
            page_count = doc.page_count  # save before close
            doc.close()
            
            # Filter None values from OCR results
            text_parts_clean = [t for t in text_parts if t]
            full_text = "\n\n".join(text_parts_clean)
            logger.success(f"  [PDF-OCR] Fertig: {len(full_text)} Zeichen aus {page_count} Seiten")
            
            return full_text.strip(), image_paths
            
        except Exception as e:
            logger.error(f"[ERROR] PDF-OCR fehlgeschlagen: {e}")
            return "", []
    
    def get_page_count(self, pdf_path: Path) -> int:
        """
        Gibt Anzahl der Seiten in PDF zurück
        
        Args:
            pdf_path: Pfad zum PDF
            
        Returns:
            Anzahl Seiten (oder 0 bei Fehler)
        """
        try:
            doc = fitz.open(str(pdf_path))
            page_count = doc.page_count
            doc.close()
            return page_count
        except Exception as e:
            logger.error(f"[ERROR] PDF Page-Count fehlgeschlagen: {e}")
            return 0
