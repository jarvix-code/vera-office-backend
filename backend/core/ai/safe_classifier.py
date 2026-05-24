"""
Safe Classifier - Active Learning statt "UNBEKANNT"
Klassifiziert nur wenn sicher! Bei Unsicherheit: FRAGE USER!

BORIS' FEEDBACK (2026-03-28):
- Feedback 1: "Warum fragt VERA nicht den User?"
- Feedback 2: "Kategorien sind UNBEGRENZT, nicht vordefiniert!"

LÖSUNG:
- Confidence >= Threshold → Auto-klassifizieren
- Confidence < Threshold → Active Learning Dialog (User fragen!)
- User erklärt FREI → VERA extrahiert Kategorie dynamisch
"""
import logging
from typing import Dict, Optional, List
from .classifier import DocumentClassifier
from .dynamic_categories import dynamic_categories

# RAG Engine ist optional
try:
    from .rag_engine import RAGEngine
    HAS_RAG = True
except ImportError:
    RAGEngine = None
    HAS_RAG = False

logger = logging.getLogger(__name__)


class SafeClassifier:
    """
    Safe Document Classifier mit Confidence-Threshold.
    
    Workflow:
    1. RAG: Suche ähnliche Dokumente
    2. LLM: Klassifiziere mit Confidence
    3. Check: Confidence >= Threshold?
       - JA → Klassifikation akzeptieren
       - NEIN → "UNBEKANNT" + Review anfordern
    """
    
    def __init__(
        self,
        min_confidence: float = 0.95,  # UPDATED: 85% → 95% (Boris' Requirement)
        quick_confirm_threshold: float = 0.75,  # NEW: Quick Confirm Stufe 2
        use_rag: bool = True
    ):
        """
        Initialize Safe Classifier with 3-level confidence system.
        
        BORIS' 3-STUFEN SYSTEM (2026-03-28):
        - Stufe 1 (≥95%): Auto-Klassifikation (keine User-Action)
        - Stufe 2 (75-95%): Quick Confirm (1-Click Bestätigung)
        - Stufe 3 (<75%): Volle Erklärung nötig
        
        Args:
            min_confidence: Threshold für Auto-Klassifikation (Stufe 1)
            quick_confirm_threshold: Threshold für Quick Confirm (Stufe 2)
            use_rag: RAG für Kontext nutzen
        """
        self.min_confidence = min_confidence
        self.quick_confirm_threshold = quick_confirm_threshold
        self.use_rag = use_rag
        
        # Initialize components
        self.classifier = DocumentClassifier()
        
        if use_rag:
            try:
                self.rag = RAGEngine()
                logger.info("[SafeClassifier] RAG engine initialized")
            except Exception as e:
                logger.warning(f"[SafeClassifier] RAG init failed: {e}")
                self.rag = None
        else:
            self.rag = None
    
    def classify_with_confidence_levels(
        self,
        text: str,
        user: Optional[object] = None,
        user_name: str = "Boris"
    ) -> Dict:
        """
        Klassifiziere mit 3-Stufen Confidence System (Boris' Requirement).
        
        STUFE 1 (≥95%): Auto-Klassifikation
        - VERA handelt selbständig
        - Keine User-Action nötig
        
        STUFE 2 (75-95%): Quick Confirm
        - VERA fragt: "Ich glaube das gehört zu X. Bin ich da richtig?"
        - User: 1-Click Bestätigung ("Ja, richtig")
        - Reduziert User-Aufwand massiv!
        
        STUFE 3 (<75%): Volle Erklärung
        - VERA: "Hey Boris, was ist das?"
        - User muss ausführlich erklären
        
        Args:
            text: OCR-Text
            user: User object (optional, for personalization)
            user_name: User name for personalization
        
        Returns:
            STUFE 1 (≥95%):
            {
                "action": "auto_classified",
                "class": str,
                "confidence": float,
                "user_action_needed": False
            }
            
            STUFE 2 (75-95%):
            {
                "action": "confirm_with_suggestion",
                "vorschlag": str,
                "confidence": float,
                "frage": str,
                "user_action_needed": True,
                "can_quick_confirm": True
            }
            
            STUFE 3 (<75%):
            {
                "action": "needs_explanation",
                "confidence": float,
                "frage": str,
                "user_action_needed": True,
                "can_quick_confirm": False
            }
        """
        
        # Optional: RAG Context holen
        rag_context_used = False
        if self.rag:
            try:
                context = self.rag.search(text, top_k=3)
                if context and len(context) > 0:
                    rag_context_used = True
                    logger.debug(f"[SafeClassifier] RAG: {len(context)} results")
            except Exception as e:
                logger.warning(f"[SafeClassifier] RAG search failed: {e}")
        
        # Klassifiziere
        try:
            result = self.classifier.classify(text, use_few_shot=True)
            
            category = result.get("category", "unknown")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            
            # 3-STUFEN CONFIDENCE CHECK (Boris' System)
            
            # STUFE 1: SEHR SICHER (≥95%)
            if confidence >= self.min_confidence:
                logger.info(f"[SafeClassifier] ✓ STUFE 1 (Auto): {category} ({confidence:.2%})")
                
                return {
                    "action": "auto_classified",
                    "class": category,
                    "confidence": confidence,
                    "user_action_needed": False,
                    "reasoning": reasoning,
                    "rag_context": rag_context_used
                }
            
            # STUFE 2: MITTEL SICHER (75-95%) → Quick Confirm
            elif confidence >= self.quick_confirm_threshold:
                logger.info(f"[SafeClassifier] ⚠ STUFE 2 (Quick Confirm): {category} ({confidence:.2%})")
                
                return {
                    "action": "confirm_with_suggestion",
                    "vorschlag": category,
                    "confidence": confidence,
                    "frage": f"Ich glaube das gehört zu '{category}'. Bin ich da richtig?",
                    "user_action_needed": True,
                    "can_quick_confirm": True,
                    "reasoning": reasoning,
                    "rag_context": rag_context_used
                }
            
            # STUFE 3: UNSICHER (<75%) → Volle Erklärung
            else:
                logger.warning(f"[SafeClassifier] ❌ STUFE 3 (Needs Explanation): {confidence:.2%}")
                
                return {
                    "action": "needs_explanation",
                    "confidence": confidence,
                    "frage": f"Hey {user_name}, ich kann das Dokument nicht zuordnen. Was ist das?",
                    "user_action_needed": True,
                    "can_quick_confirm": False,
                    "reasoning": f"Zu unsicher ({confidence:.0%} < {self.quick_confirm_threshold:.0%})",
                    "rag_context": rag_context_used
                }
        
        except Exception as e:
            logger.error(f"[SafeClassifier] Classification failed: {e}", exc_info=True)
            
            # Error → STUFE 3 (Volle Erklärung)
            return {
                "action": "needs_explanation",
                "confidence": 0.0,
                "frage": f"Hey {user_name}, ich kann das Dokument nicht einordnen. Was ist das?",
                "user_action_needed": True,
                "can_quick_confirm": False,
                "reasoning": f"Fehler: {str(e)}",
                "rag_context": rag_context_used
            }
    
    def _get_alternatives(self, main_suggestion: str, max_alternatives: int = 2) -> List[str]:
        """
        Get alternative category suggestions.
        
        For now: return most common user-defined categories.
        TODO: Could use LLM to suggest alternatives based on text.
        """
        # Get most used categories from dynamic system
        all_categories = dynamic_categories.get_all_categories(sort_by="count")
        
        alternatives = []
        for cat in all_categories[:5]:  # Top 5
            cat_name = cat["name"]
            if cat_name != main_suggestion:
                alternatives.append(cat_name)
            
            if len(alternatives) >= max_alternatives:
                break
        
        return alternatives
    
    def _build_question(self, vorschlag: str, confidence: float, user_name: str) -> str:
        """
        Build natural question for user.
        
        Examples:
            confidence=0.75: "Ich bin unsicher (75% sicher). Ist das eine Rechnung?"
            confidence=0.50: "Ich kann das nicht zuordnen. Was ist das für ein Dokument?"
        """
        confidence_pct = int(confidence * 100)
        
        if confidence >= 0.70:
            # Medium confidence → suggest with uncertainty
            return (
                f"Hey {user_name}, ich bin unsicher ({confidence_pct}% sicher). "
                f"Ist das eine {vorschlag}?"
            )
        elif confidence >= 0.50:
            # Low confidence → open question
            return (
                f"Hey {user_name}, ich kann das Dokument nicht zuordnen. "
                f"Was ist das für ein Dokument?"
            )
        else:
            # Very low confidence → completely lost
            return (
                f"Hey {user_name}, ich verstehe dieses Dokument nicht. "
                f"Kannst du mir helfen? Was ist das?"
            )
    
    def learn_from_user_explanation(
        self,
        text: str,
        user_explanation: str,
        user_id: int,
        user_name: str
    ) -> Dict:
        """
        Learn from user's free-text explanation.
        
        Boris' Workflow:
        1. User writes: "Das ist ein Wartungsvertrag für Röntgengeräte"
        2. Extract category: "Wartungsvertrag (Medizingeräte)"
        3. Add to dynamic categories
        4. Update RAG with this info
        
        Args:
            text: Original OCR text
            user_explanation: User's free-text explanation
            user_id: User ID
            user_name: User name
        
        Returns:
            {
                "status": "learned",
                "category": str,
                "message": str
            }
        """
        # Extract category from user explanation
        category_info = dynamic_categories.extract_category_from_explanation(user_explanation)
        
        # Add to dynamic categories (or merge if similar exists)
        result = dynamic_categories.add_new_category(
            category_info,
            user_id,
            user_name
        )
        
        logger.info(
            f"[SafeClassifier] Learned from {user_name}: "
            f"'{category_info['full_name']}' (status: {result['status']})"
        )
        
        # TODO: Update RAG with this document + explanation
        # self.rag.add_document(text, category_info, user_explanation)
        
        return {
            "status": "learned",
            "category": category_info["full_name"],
            "message": f"Danke! Ich habe gelernt: {category_info['full_name']}"
        }
    
    def set_thresholds(
        self, 
        min_confidence: Optional[float] = None,
        quick_confirm_threshold: Optional[float] = None
    ):
        """
        Update confidence thresholds (3-Stufen System).
        
        Args:
            min_confidence: Neuer Threshold für Auto-Klassifikation (Stufe 1)
            quick_confirm_threshold: Neuer Threshold für Quick Confirm (Stufe 2)
        """
        if min_confidence is not None:
            if not 0.0 <= min_confidence <= 1.0:
                raise ValueError("min_confidence must be between 0.0 and 1.0")
            
            old = self.min_confidence
            self.min_confidence = min_confidence
            logger.info(f"[SafeClassifier] Auto threshold: {old:.2%} → {min_confidence:.2%}")
        
        if quick_confirm_threshold is not None:
            if not 0.0 <= quick_confirm_threshold <= 1.0:
                raise ValueError("quick_confirm_threshold must be between 0.0 and 1.0")
            
            old = self.quick_confirm_threshold
            self.quick_confirm_threshold = quick_confirm_threshold
            logger.info(f"[SafeClassifier] Quick Confirm threshold: {old:.2%} → {quick_confirm_threshold:.2%}")
    
    def get_stats(self) -> Dict:
        """
        Get classifier statistics (3-Stufen System).
        
        Returns:
            Statistics dict
        """
        return {
            "min_confidence": self.min_confidence,
            "quick_confirm_threshold": self.quick_confirm_threshold,
            "stufe_1_auto": f"≥{self.min_confidence:.0%}",
            "stufe_2_quick_confirm": f"{self.quick_confirm_threshold:.0%}-{self.min_confidence:.0%}",
            "stufe_3_needs_explanation": f"<{self.quick_confirm_threshold:.0%}",
            "rag_enabled": self.rag is not None,
            "classifier_available": self.classifier.llm.is_available()
        }


# Singleton instance
safe_classifier = SafeClassifier()
