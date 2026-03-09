"""
Document Classifier - Uses Mistral 7B for classification with dynamic few-shot learning.
Integrates YAML template knowledge for category awareness.
"""
import json
import logging
from typing import Dict, List, Optional
from .llm_router import llm_router
from .llm_manager import llm as llm_manager  # Keep for get_config() calls
from .feedback_store import feedback_store
from .template_knowledge import get_all_categories, get_categories_prompt_text
from .brain import brain
from .few_shot_examples import get_examples_by_keywords, format_example_for_prompt

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Classifies documents using LLM Router (always Local for classification)."""
    
    def __init__(self):
        # Get Local LLM via Router for classification (Background task)
        self.llm = llm_router.get_llm("doc_classification")
        self.llm_manager = llm_manager  # Keep for config access
        self.feedback = feedback_store
        self._industry = "allgemein"
    
    def set_industry(self, industry: str):
        """Set industry for template-aware classification."""
        self._industry = industry
    
    def classify(
        self, 
        ocr_text: str, 
        categories: Optional[List[Dict[str, str]]] = None,
        use_few_shot: bool = True
    ) -> Dict:
        """
        Classify document based on OCR text.
        
        Args:
            ocr_text: OCR extracted text
            categories: List of category dicts (auto-loaded from YAML if None)
            use_few_shot: Include similar examples in prompt
        
        Returns:
            {
                'category': str,
                'confidence': float,
                'reasoning': str,
                'available': bool
            }
        """
        # 🧠 Brain-Hints: Prüfe ob VERA das schon kennt
        brain_hints = brain.get_all_hints_for_document(
            keywords=[w.lower() for w in ocr_text[:500].split()[:20] if len(w) > 3]
        )
        if brain_hints and brain_hints[0]["confidence"] >= 0.85:
            hint = brain_hints[0]
            logger.info(f"🧠 Brain-Hint: {hint['source']} → {hint['category']} ({hint['confidence']:.0%})")
            return {
                'category': hint['category'],
                'confidence': hint['confidence'],
                'reasoning': f"Aus Erfahrung gelernt ({hint['source']}, {hint['times_confirmed']}x bestätigt)",
                'available': True,
                'brain_hint': True
            }
        
        if not self.llm or not self.llm.is_available():
            logger.warning("Classification LLM not available - trying keyword fallback")
            return self._keyword_fallback(ocr_text, categories)
        
        # Auto-load categories from YAML templates if not provided
        if categories is None:
            categories = get_all_categories(self._industry)
        
        # Build prompt
        prompt = self._build_prompt(ocr_text, categories, use_few_shot)
        
        # Generate response
        response = self.llm.generate(
            prompt,
            max_tokens=300,
            temperature=0.1,
            stop=["</s>", "\n\n"]
        )
        
        if not response:
            return {
                'category': 'unknown',
                'confidence': 0.0,
                'reasoning': 'LLM generation failed',
                'available': True
            }
        
        result = self._parse_response(response, categories)
        result['available'] = True
        return result
    
    def _build_prompt(
        self, 
        ocr_text: str, 
        categories: List[Dict[str, str]],
        use_few_shot: bool
    ) -> str:
        """Build classification prompt with template knowledge and few-shot examples."""
        
        prompt = """<s>[INST] Du bist ein Dokumenten-Klassifizierungs-Assistent für ein deutsches KMU.
Klassifiziere das Dokument basierend auf dem OCR-Text in eine der verfügbaren Kategorien.

Verfügbare Kategorien:
"""
        
        for cat in categories:
            desc = cat.get('description', cat.get('folder_display', ''))
            prompt += f"\n- {cat['name']}: {desc}"
        
        # Few-shot examples: (1) Static examples, (2) Feedback store
        if use_few_shot:
            # 1. Static examples from few_shot_examples.py (immer dabei, breit gefächert)
            keywords = [w.lower() for w in ocr_text[:500].split() if len(w) > 3]
            static_examples = get_examples_by_keywords(keywords, limit=2)
            
            # 2. Dynamic examples from feedback store (user-specific, gelernt)
            similar_examples = self.feedback.get_similar_examples(ocr_text[:2000], n=3)
            
            if static_examples or similar_examples:
                prompt += "\n\nBeispiel-Klassifizierungen:\n"
                
                # Static examples first (hohe Qualität)
                for i, ex in enumerate(static_examples, 1):
                    prompt += f"\nBeispiel {i} (Referenz):\n{format_example_for_prompt(ex)}\n"
                
                # Feedback examples (gelernte Muster)
                for i, ex in enumerate(similar_examples, len(static_examples) + 1):
                    snippet = ex['ocr_snippet'][:200].replace('\n', ' ')
                    prompt += f"\nBeispiel {i} (gelernt):\nText: {snippet}...\nKategorie: {ex['category']}\n"
        
        # Document to classify
        prompt += f"\n\nDokument zum Klassifizieren:\n{ocr_text[:1500]}\n\n"
        
        prompt += """Antworte als JSON:
{
  "category": "kategorie_name",
  "confidence": 0.95,
  "reasoning": "kurze Begründung"
}
[/INST]"""
        
        return prompt
    
    def _parse_response(self, response: str, categories: List[Dict[str, str]]) -> Dict:
        """Parse LLM response into structured result."""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                
                category = data.get('category', 'unknown')
                confidence = float(data.get('confidence', 0.0))
                reasoning = data.get('reasoning', 'No reasoning provided')
                
                # Validate category exists
                category_names = [c['name'] for c in categories]
                if category not in category_names:
                    # Try fuzzy match
                    for cn in category_names:
                        if cn.lower() == category.lower() or cn in category.lower() or category in cn.lower():
                            category = cn
                            break
                    else:
                        logger.warning(f"Invalid category '{category}' - defaulting to unknown")
                        category = 'unknown'
                        confidence = 0.0
                
                confidence = max(0.0, min(1.0, confidence))
                
                return {
                    'category': category,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        
        # Fallback: extract category name from text
        for cat in categories:
            if cat['name'].lower() in response.lower():
                return {
                    'category': cat['name'],
                    'confidence': 0.5,
                    'reasoning': 'Extracted from unstructured response'
                }
        
        return {
            'category': 'unknown',
            'confidence': 0.0,
            'reasoning': 'Could not parse classification result'
        }
    
    def _keyword_fallback(self, ocr_text: str, categories: Optional[List[Dict]] = None) -> Dict:
        """Simple keyword-based classification when LLM is unavailable."""
        if categories is None:
            categories = get_all_categories(self._industry)
        
        text_lower = ocr_text.lower()
        
        # Simple keyword matching
        keyword_map = {
            'rechnung_eingang': ['rechnung', 'invoice', 'rechnungsnummer', 'rechnungsdatum', 'netto', 'brutto', 'mwst'],
            'rechnung_ausgang': ['ausgangsrechnung'],
            'kontoauszug': ['kontoauszug', 'saldo', 'bankverbindung', 'iban'],
            'arbeitsvertrag': ['arbeitsvertrag', 'anstellungsvertrag', 'arbeitsverhältnis'],
            'mietvertrag': ['mietvertrag', 'miete', 'vermieter', 'mieter'],
            'steuerbescheid': ['steuerbescheid', 'finanzamt', 'einkommensteuer'],
            'mahnung_eingang': ['mahnung', 'zahlungserinnerung', 'fällig'],
            'versicherungspolice': ['versicherung', 'police', 'versicherungsnummer'],
            'lohnabrechnung': ['lohnabrechnung', 'gehaltsabrechnung', 'bruttolohn'],
            'angebot': ['angebot', 'kostenvoranschlag'],
        }
        
        best_match = None
        best_score = 0
        
        for cat_name, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_match = cat_name
        
        if best_match and best_score >= 2:
            confidence = min(0.7, 0.3 + best_score * 0.1)
            return {
                'category': best_match,
                'confidence': confidence,
                'reasoning': f'Keyword-Fallback: {best_score} keywords matched',
                'available': False
            }
        
        return {
            'category': 'unknown',
            'confidence': 0.0,
            'reasoning': 'LLM unavailable and no keyword match',
            'available': False
        }
    
    def should_auto_file(self, confidence: float) -> bool:
        """Check if confidence is high enough for automatic filing."""
        threshold = self.llm_manager.get_config('confidence_threshold') or 0.80
        return confidence >= threshold
    
    def should_auto_confirm(self, confidence: float) -> bool:
        """Check if confidence is high enough for auto-confirmation."""
        threshold = self.llm_manager.get_config('auto_confirm_threshold') or 0.95
        return confidence >= threshold


# Global instance
classifier = DocumentClassifier()
