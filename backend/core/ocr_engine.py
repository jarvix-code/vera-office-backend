"""
VERA Office - OCR Engine
Texterkennung mit PaddleOCR (besser als Tesseract bei Handyfotos)
"""
from pathlib import Path
from typing import Optional, List, Tuple
from loguru import logger
from backend.config import config

# PaddleOCR Import (lazy loading)
_paddleocr_instance = None
_paddleocr_init_failed = False  # Sentinel: verhindert wiederholte Init-Versuche


def get_ocr_engine():
    """
    Lazy Loading der OCR-Engine (nur beim ersten Aufruf initialisieren).
    Nach einem gescheiterten Init wird kein weiterer Versuch unternommen.
    """
    global _paddleocr_instance, _paddleocr_init_failed

    if _paddleocr_init_failed:
        return None

    if _paddleocr_instance is None:
        try:
            from paddleocr import PaddleOCR

            logger.info("[CONFIG] Initialisiere PaddleOCR...")
            _paddleocr_instance = PaddleOCR(
                use_angle_cls=True,  # Automatische Textrotations-Erkennung
                lang=config.OCR_LANGUAGE,  # 'de' für Deutsch
                use_gpu=config.OCR_GPU,  # CPU-Modus für Mini-PC
                show_log=False  # Weniger Spam in Logs
            )
            logger.success("[OK] PaddleOCR initialisiert")

        except Exception as e:
            logger.error(f"[ERROR] Fehler bei PaddleOCR-Initialisierung: {e}")
            _paddleocr_init_failed = True
            return None

    return _paddleocr_instance


class OCREngine:
    """
    OCR-Wrapper für Dokumenten-Texterkennung
    """
    
    def __init__(self):
        self.engine = None  # Lazy loading
        
    def extract_text(self, image_path: Path) -> Optional[str]:
        """
        Extrahiert Text aus Bild
        
        Args:
            image_path: Pfad zum Bild
            
        Returns:
            Erkannter Text oder None bei Fehler
        """
        try:
            if self.engine is None:
                self.engine = get_ocr_engine()

            if self.engine is None:
                logger.warning(f"[WARNING] OCR-Engine nicht verfügbar, überspringe: {image_path.name}")
                return None

            logger.info(f" Starte OCR: {image_path.name}")
            
            # OCR ausführen
            result = self.engine.ocr(str(image_path), cls=True)
            
            if not result or not result[0]:
                logger.warning(f"[WARNING] Kein Text erkannt in {image_path.name}")
                return None
            
            # Text aus Result extrahieren
            text_lines = []
            for line in result[0]:
                if line and len(line) > 1:
                    text = line[1][0]  # [1] = (text, confidence), [0] = text
                    confidence = line[1][1]  # confidence score
                    
                    # Nur Text mit ausreichender Konfidenz
                    if confidence > 0.5:
                        text_lines.append(text)
            
            full_text = "\n".join(text_lines)
            
            if full_text.strip():
                logger.success(f"[OK] OCR erfolgreich: {len(text_lines)} Zeilen, {len(full_text)} Zeichen")
                return full_text
            else:
                logger.warning(f"[WARNING] OCR lieferte keinen Text: {image_path.name}")
                return None
                
        except Exception as e:
            logger.error(f"[ERROR] OCR-Fehler bei {image_path.name}: {e}")
            return None
    
    def extract_text_with_boxes(self, image_path: Path) -> Optional[List[Tuple[str, float, List]]]:
        """
        Extrahiert Text mit Bounding-Boxes (für detaillierte Analyse)
        
        Args:
            image_path: Pfad zum Bild
            
        Returns:
            Liste von (text, confidence, bbox) oder None
        """
        try:
            if self.engine is None:
                self.engine = get_ocr_engine()

            if self.engine is None:
                return None

            result = self.engine.ocr(str(image_path), cls=True)
            
            if not result or not result[0]:
                return None
            
            structured_result = []
            for line in result[0]:
                if line and len(line) > 1:
                    bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    text = line[1][0]
                    confidence = line[1][1]
                    
                    structured_result.append((text, confidence, bbox))
            
            return structured_result if structured_result else None
            
        except Exception as e:
            logger.error(f"[ERROR] OCR-Fehler: {e}")
            return None
