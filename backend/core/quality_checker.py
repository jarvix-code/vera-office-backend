"""
VERA Office - Quality Checker
Automatische KI-Qualitätsprüfung nach OCR + PDF-Generierung
"""
import cv2
import json
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
from loguru import logger


class QualityChecker:
    """
    Prüft die Qualität eines verarbeiteten Dokuments:
    - OCR-Confidence (Text plausibel?)
    - Bildqualität (Schärfe, Helligkeit, Kontrast)
    - Vollständigkeit (Textmenge vs. Bildgröße)
    """

    def check(
        self,
        image_path: Path,
        ocr_text: Optional[str],
    ) -> Tuple[float, List[str]]:
        """
        Führt alle Qualitäts-Checks durch.

        Returns:
            (quality_score 0-100, list of issue strings)
        """
        issues: List[str] = []
        scores: List[float] = []

        # 1. OCR-Confidence
        ocr_score = self._check_ocr(ocr_text, issues)
        scores.append(ocr_score)

        # 2. Bildqualität
        img_score = self._check_image_quality(image_path, issues)
        scores.append(img_score)

        # 3. Vollständigkeit (Text vs. Bildgröße)
        completeness_score = self._check_completeness(image_path, ocr_text, issues)
        scores.append(completeness_score)

        # Gewichteter Score: OCR 40%, Bild 35%, Vollständigkeit 25%
        weights = [0.40, 0.35, 0.25]
        quality_score = sum(s * w for s, w in zip(scores, weights))
        quality_score = max(0, min(100, round(quality_score, 1)))

        logger.info(
            f"[STATS] Quality Check: score={quality_score} "
            f"(ocr={ocr_score:.0f}, img={img_score:.0f}, compl={completeness_score:.0f}) "
            f"issues={issues}"
        )
        return quality_score, issues

    def _check_ocr(self, ocr_text: Optional[str], issues: List[str]) -> float:
        if not ocr_text or not ocr_text.strip():
            issues.append("Kein Text erkannt (OCR leer)")
            return 0.0

        text = ocr_text.strip()
        length = len(text)

        if length < 10:
            issues.append(f"Sehr wenig Text erkannt ({length} Zeichen)")
            return 20.0
        if length < 50:
            issues.append(f"Wenig Text erkannt ({length} Zeichen)")
            return 50.0
        if length < 100:
            return 75.0
        return 100.0

    def _check_image_quality(self, image_path: Path, issues: List[str]) -> float:
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                issues.append("Bild konnte nicht geladen werden")
                return 0.0

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            score = 100.0

            # Schärfe (Laplacian variance)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < 50:
                issues.append(f"Bild unscharf (Laplacian={laplacian_var:.0f})")
                score -= 40
            elif laplacian_var < 100:
                issues.append(f"Bild leicht unscharf (Laplacian={laplacian_var:.0f})")
                score -= 15

            # Helligkeit
            mean_brightness = gray.mean()
            if mean_brightness < 60:
                issues.append(f"Bild zu dunkel (Helligkeit={mean_brightness:.0f})")
                score -= 30
            elif mean_brightness > 240:
                issues.append(f"Bild überbelichtet (Helligkeit={mean_brightness:.0f})")
                score -= 20

            # Kontrast (Standardabweichung)
            contrast = gray.std()
            if contrast < 20:
                issues.append(f"Niedriger Kontrast (std={contrast:.0f})")
                score -= 25

            return max(0, score)
        except Exception as e:
            issues.append(f"Bildanalyse-Fehler: {e}")
            return 50.0

    def _check_completeness(
        self, image_path: Path, ocr_text: Optional[str], issues: List[str]
    ) -> float:
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return 50.0

            h, w = img.shape[:2]
            pixel_count = h * w
            text_len = len(ocr_text.strip()) if ocr_text else 0

            # Erwartete Textmenge basierend auf Bildgröße
            # Ein A4-Dokument bei 300dpi ~ 2480x3508 ~ 8.7M Pixel, ca. 2000-5000 Zeichen
            expected_chars = pixel_count / 5000  # grobe Heuristik
            
            if text_len == 0:
                issues.append("Kein Text bei vorhandenem Bild")
                return 0.0

            ratio = text_len / max(expected_chars, 1)
            if ratio < 0.1:
                issues.append("Sehr wenig Text für Bildgröße")
                return 30.0
            if ratio < 0.3:
                issues.append("Wenig Text für Bildgröße")
                return 60.0
            return 100.0
        except Exception:
            return 50.0

    @staticmethod
    def determine_status(quality_score: float) -> str:
        """
        Bestimmt den Dokumentstatus basierend auf Quality Score.
        
        >= 80: 'processed' (weiter in Pipeline)
        40-79: 'needs_review' (User-Prüfung)
        < 40:  'needs_rescan' (nochmal fotografieren)
        """
        if quality_score >= 80:
            return "processed"
        elif quality_score >= 40:
            return "needs_review"
        else:
            return "needs_rescan"

    @staticmethod
    def issues_to_json(issues: List[str]) -> str:
        return json.dumps(issues, ensure_ascii=False)

    @staticmethod
    def issues_from_json(json_str: Optional[str]) -> List[str]:
        if not json_str:
            return []
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return []
