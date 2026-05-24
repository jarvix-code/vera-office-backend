"""
Vision Quality Checker – STUB (LLaVA entfernt).
PaddleOCR übernimmt Texterkennung; Vision-LLM wird nicht mehr benötigt.
Alle Aufrufe erhalten einen sofortigen Passthrough mit available=False.
"""
from typing import Dict


class VisionQualityChecker:
    """No-op stub. Immer available=False zurückgeben."""

    def check_quality(self, image_path: str, language: str = "de") -> Dict:
        return {
            'available': False,
            'quality_score': None,
            'issues': [],
            'suggestion': 'Vision-LLM deaktiviert',
        }


# Global instance
vision_checker = VisionQualityChecker()
