"""
VERA Office - PDF Generator
Erstellt durchsuchbare PDFs aus verarbeiteten Bildern mit OCR-Layer
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional
from loguru import logger
from backend.config import config


class PDFGenerator:
    """
    Erzeugt PDFs aus Bildern mit eingebettetem OCR-Text
    """
    
    def __init__(self):
        self.dpi = config.IMAGE_DPI
        
    def create_pdf_from_images(
        self, 
        image_paths: List[Path], 
        output_path: Path,
        ocr_text: Optional[str] = None
    ) -> bool:
        """
        Erstellt PDF aus einer oder mehreren Bilddateien
        
        Args:
            image_paths: Liste von Bildpfaden (für mehrseitige Dokumente)
            output_path: Pfad für Output-PDF
            ocr_text: Optional: OCR-Text für Volltextsuche
            
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            logger.info(f"📄 Erstelle PDF: {output_path.name} ({len(image_paths)} Seite(n))")
            
            # Neues PDF-Dokument
            pdf_document = fitz.open()
            
            for idx, image_path in enumerate(image_paths):
                if not image_path.exists():
                    logger.error(f"❌ Bild nicht gefunden: {image_path}")
                    continue
                
                # Öffne Bild
                img_doc = fitz.open(str(image_path))
                
                # Konvertiere zu PDF-Seite
                pdf_bytes = img_doc.convert_to_pdf()
                img_pdf = fitz.open("pdf", pdf_bytes)
                
                # Füge Seite zum Hauptdokument hinzu
                pdf_document.insert_pdf(img_pdf)
                
                img_doc.close()
                img_pdf.close()
                
                logger.debug(f"  ✅ Seite {idx + 1}/{len(image_paths)} hinzugefügt")
            
            # OCR-Text als unsichtbaren Layer hinzufügen (für Volltextsuche)
            if ocr_text and ocr_text.strip():
                self._add_text_layer(pdf_document, ocr_text)
            
            # Speichern
            output_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_document.save(
                str(output_path),
                garbage=4,  # Optimiere Dateigröße
                deflate=True  # Kompression
            )
            pdf_document.close()
            
            file_size_kb = output_path.stat().st_size / 1024
            logger.success(f"✅ PDF erstellt: {output_path.name} ({file_size_kb:.1f} KB)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler bei PDF-Erstellung: {e}")
            return False
    
    def _add_text_layer(self, pdf_document: fitz.Document, text: str):
        """
        Fügt unsichtbaren OCR-Text zur ersten Seite hinzu (für Volltextsuche)
        """
        try:
            if not pdf_document or pdf_document.page_count == 0:
                return
            
            page = pdf_document[0]
            
            # Füge Text als unsichtbare Annotation hinzu
            # (Alternative: TextPage, aber Annotation ist einfacher)
            page.insert_text(
                (0, 0),  # Position (wird unsichtbar sein)
                text,
                fontsize=0.1,  # Minimale Größe
                color=(1, 1, 1),  # Weiß (unsichtbar auf weißem Hintergrund)
                overlay=False
            )
            
            logger.debug("  ✅ OCR-Text-Layer hinzugefügt")
            
        except Exception as e:
            logger.debug(f"  ⚠️ Konnte OCR-Layer nicht hinzufügen: {e}")
    
    def merge_pdfs(self, pdf_paths: List[Path], output_path: Path) -> bool:
        """
        Fügt mehrere PDFs zusammen
        
        Args:
            pdf_paths: Liste von PDF-Dateien
            output_path: Ziel-PDF
            
        Returns:
            True wenn erfolgreich
        """
        try:
            logger.info(f"📄 Füge {len(pdf_paths)} PDFs zusammen")
            
            merged_pdf = fitz.open()
            
            for pdf_path in pdf_paths:
                if not pdf_path.exists():
                    logger.warning(f"⚠️ PDF nicht gefunden: {pdf_path}")
                    continue
                    
                pdf = fitz.open(str(pdf_path))
                merged_pdf.insert_pdf(pdf)
                pdf.close()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            merged_pdf.save(str(output_path), garbage=4, deflate=True)
            merged_pdf.close()
            
            logger.success(f"✅ PDFs zusammengeführt: {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Fehler beim PDF-Merge: {e}")
            return False
