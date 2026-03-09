"""
Vision-based Document Quality Checker.
Uses Vision-LLM (LLaVA) to assess document photo quality for OCR.
Complements the heuristic quality check from Sprint 1.
"""
import json
import logging
from typing import Dict, Optional
from .llm_manager import llm

logger = logging.getLogger(__name__)

QUALITY_PROMPT = """Analyze this document photo for OCR readiness. Check:
1. Sharpness: Is the text sharp and readable?
2. Completeness: Is the entire document visible, no cut-off corners?
3. Lighting: Is the lighting even, no shadows or glare?
4. Orientation: Is the document properly oriented?
5. Overall: Would OCR produce good results?

Respond in JSON:
{
  "readable": true/false,
  "sharp": true/false,
  "complete": true/false,
  "good_lighting": true/false,
  "quality_score": 0.0-1.0,
  "issues": ["issue1", "issue2"],
  "suggestion": "brief improvement suggestion or 'Good quality'"
}"""

QUALITY_PROMPT_DE = """Analysiere dieses Dokument-Foto für OCR-Verarbeitung. Prüfe:
1. Schärfe: Ist der Text scharf und lesbar?
2. Vollständigkeit: Ist das gesamte Dokument sichtbar, keine abgeschnittenen Ecken?
3. Beleuchtung: Ist die Beleuchtung gleichmäßig, keine Schatten oder Reflexionen?
4. Ausrichtung: Ist das Dokument richtig ausgerichtet?
5. Gesamt: Würde OCR gute Ergebnisse liefern?

Antworte als JSON:
{
  "readable": true/false,
  "sharp": true/false,
  "complete": true/false,
  "good_lighting": true/false,
  "quality_score": 0.0-1.0,
  "issues": ["Problem1", "Problem2"],
  "suggestion": "Kurzer Verbesserungsvorschlag oder 'Gute Qualität'"
}"""


class VisionQualityChecker:
    """Checks document photo quality using Vision-LLM."""
    
    def __init__(self):
        self.llm = llm
    
    def check_quality(self, image_path: str, language: str = "de") -> Dict:
        """
        Check document image quality using Vision-LLM.
        
        Args:
            image_path: Path to document image
            language: 'de' or 'en' for prompt language
        
        Returns:
            Quality assessment dict with score, issues, suggestions
        """
        if not self.llm.is_vision_available():
            logger.info("Vision-LLM not available, skipping vision quality check")
            return {
                'available': False,
                'quality_score': None,
                'issues': [],
                'suggestion': 'Vision-LLM nicht verfügbar',
            }
        
        prompt = QUALITY_PROMPT_DE if language == "de" else QUALITY_PROMPT
        
        response = self.llm.analyze_image(image_path, prompt=prompt, max_tokens=400)
        
        if not response:
            return {
                'available': True,
                'quality_score': None,
                'issues': [],
                'suggestion': 'Vision-Analyse fehlgeschlagen',
            }
        
        return self._parse_response(response)
    
    def _parse_response(self, response: str) -> Dict:
        """Parse Vision-LLM response into quality assessment."""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                
                quality_score = float(data.get('quality_score', 0.5))
                quality_score = max(0.0, min(1.0, quality_score))
                
                return {
                    'available': True,
                    'readable': data.get('readable', True),
                    'sharp': data.get('sharp', True),
                    'complete': data.get('complete', True),
                    'good_lighting': data.get('good_lighting', True),
                    'quality_score': quality_score,
                    'issues': data.get('issues', []),
                    'suggestion': data.get('suggestion', ''),
                }
        except Exception as e:
            logger.error(f"Failed to parse vision response: {e}")
        
        return {
            'available': True,
            'quality_score': 0.5,
            'issues': ['Antwort konnte nicht geparst werden'],
            'suggestion': response[:200],
        }


# Global instance
vision_checker = VisionQualityChecker()
