"""
VERA Office - Image Processor
Bildverarbeitung: Kantenerkennung, Perspektivkorrektur, Kontrast, Kompression
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from loguru import logger
from backend.config import config


class ImageProcessor:
    """
    Verarbeitet gescannte/fotografierte Dokumente
    """
    
    def __init__(self):
        self.max_size = config.IMAGE_MAX_SIZE
        self.quality = config.IMAGE_QUALITY
        
    def process(self, image_path: Path, output_path: Path) -> bool:
        """
        Vollständige Bildverarbeitungs-Pipeline
        
        Args:
            image_path: Pfad zum Eingabebild
            output_path: Pfad für verarbeitetes Bild
            
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            logger.info(f" Verarbeite Bild: {image_path.name}")
            
            # Lade Bild
            image = cv2.imread(str(image_path))
            if image is None:
                logger.error(f"[ERROR] Konnte Bild nicht laden: {image_path}")
                return False
            
            # 1. Größenanpassung (falls zu groß)
            image = self._resize_if_needed(image)
            
            # 2. Kantenerkennung + Perspektivkorrektur
            image = self._detect_and_correct_perspective(image)
            
            # 3. Kontrastoptimierung + Schattenentfernung
            image = self._enhance_contrast(image)
            
            # 4. Rauschunterdrückung
            image = self._denoise(image)
            
            # 5. Speichern (komprimiert)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(
                str(output_path), 
                image,
                [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            )
            
            logger.success(f"[OK] Bild verarbeitet: {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Fehler bei Bildverarbeitung: {e}")
            return False
    
    def _resize_if_needed(self, image: np.ndarray) -> np.ndarray:
        """
        Skaliert Bild runter falls zu groß (Performance + Speicher)
        """
        height, width = image.shape[:2]
        max_dim = max(height, width)
        
        if max_dim > self.max_size:
            scale = self.max_size / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.debug(f" Bild skaliert: {width}x{height} -> {new_width}x{new_height}")
            
        return image
    
    def _detect_and_correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """
        Erkennt Dokumentkanten und korrigiert Perspektive
        """
        try:
            original = image.copy()
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Gaußscher Weichzeichner
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Kantenerkennung
            edges = cv2.Canny(blurred, 50, 150)
            
            # Finde Konturen
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return original
            
            # Größte Kontur finden (sollte das Dokument sein)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Approximiere zu Polygon
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # Wenn 4 Ecken gefunden -> Perspektivkorrektur
            if len(approx) == 4:
                logger.debug(" Dokumentkanten erkannt, korrigiere Perspektive")
                return self._four_point_transform(original, approx.reshape(4, 2))
            else:
                logger.debug(f"[WARNING] Keine 4 Ecken gefunden ({len(approx)} Punkte), überspringe Perspektivkorrektur")
                return original
                
        except Exception as e:
            logger.debug(f"[WARNING] Perspektivkorrektur fehlgeschlagen: {e}, nutze Original")
            return image
    
    def _four_point_transform(self, image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """
        Perspektivtransformation basierend auf 4 Eckpunkten
        """
        # Sortiere Punkte: oben-links, oben-rechts, unten-rechts, unten-links
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect
        
        # Berechne Breite des neuen Bildes
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = max(int(widthA), int(widthB))
        
        # Berechne Höhe des neuen Bildes
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = max(int(heightA), int(heightB))
        
        # Ziel-Koordinaten
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        
        # Perspektivtransformation
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        
        return warped
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """
        Sortiert 4 Punkte in konsistenter Reihenfolge
        """
        rect = np.zeros((4, 2), dtype="float32")
        
        # Summe: oben-links hat kleinste Summe, unten-rechts größte
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Differenz: oben-rechts hat kleinste Differenz, unten-links größte
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Kontrastoptimierung + Schattenentfernung
        """
        # Konvertiere zu LAB-Farbraum
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge zurück
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Rauschunterdrückung (leicht, um Text lesbar zu halten)
        """
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
