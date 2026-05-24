"""
Dynamic Categories System - VERA lernt UNBEGRENZTE Kategorien
Boris' Feedback (2026-03-28): "Dokumenttypen sind UNBEGRENZT, nicht vordefiniert!"

KONZEPT:
- KEINE vordefinierten Kategorien
- User definiert Kategorien durch freie Erklärungen
- System extrahiert Kategorien dynamisch aus User-Text
- Kategorien wachsen organisch (10 → 40 → 150+)
"""
import re
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DynamicCategorySystem:
    """
    Dynamisches Kategorien-System.
    
    Kategorien werden NICHT vordefiniert, sondern von Usern erstellt!
    
    Workflow:
    1. User schreibt freie Erklärung: "Das ist ein Wartungsvertrag für Röntgengeräte"
    2. System extrahiert: main="Wartungsvertrag", sub="Medizingeräte"
    3. Neue Kategorie wird hinzugefügt
    4. Bei ähnlichen Dokumenten: VERA erkennt sie automatisch
    """
    
    def __init__(self, categories_file: Optional[str] = None):
        """
        Initialize Dynamic Category System.
        
        Args:
            categories_file: Path to JSON file storing user-defined categories
        """
        self.categories_file = categories_file or "data/dynamic_categories.json"
        self.categories: List[Dict] = []
        
        # Common document type keywords (für Extraktion)
        self.doc_type_keywords = {
            # Verträge
            "vertrag", "contract", "vereinbarung", "kontrakt",
            "arbeitsvertrag", "mietvertrag", "wartungsvertrag", 
            "leasingvertrag", "servicevertra", "kaufvertrag",
            
            # Rechnungen/Finanzen
            "rechnung", "invoice", "beleg", "quittung",
            "angebot", "kostenvoranschlag", "mahnung",
            "zahlungserinnerung", "gutschrift", "storno",
            
            # Behörden
            "bescheid", "genehmigung", "verfügung", "auflagen",
            "behördenpost", "amtlich", "behördlich",
            
            # Personal
            "kündigung", "gehaltsabrechnung", "lohnabrechnung",
            "arbeitszeugnis", "urlaubsantrag", "bewerbung",
            
            # Allgemein
            "checkliste", "arbeitsanweisung", "protokoll",
            "anleitung", "handbuch", "dokumentation",
            "liste", "übersicht", "bericht", "auswertung",
            
            # Medizin/Praxis
            "befund", "rezept", "überweisung", "behandlungsplan",
            "patientenakte", "labor", "röntgen",
        }
        
        # Load existing categories
        self._load_categories()
    
    def extract_category_from_explanation(self, text: str) -> Dict:
        """
        Extrahiert Kategorie aus User-Erklärung.
        
        Examples:
            "Das ist ein Wartungsvertrag für Röntgengeräte"
            → {"main": "Wartungsvertrag", "sub": "Medizingeräte"}
            
            "Rechnung von unserem Laborpartner"
            → {"main": "Rechnung", "sub": "Labor"}
            
            "Behördenpost vom Gesundheitsamt"
            → {"main": "Behördenpost", "source": "Gesundheitsamt"}
        
        Args:
            text: User's free-text explanation
        
        Returns:
            {
                "main": str,              # Haupt-Kategorie
                "sub": str,               # Sub-Kategorie (optional)
                "full_name": str,         # "Wartungsvertrag (Medizingeräte)"
                "keywords": List[str],    # Extracted keywords
                "source_text": str        # Original text
            }
        """
        text_lower = text.lower()
        
        # 1. Extract main document type
        main_category = None
        for keyword in self.doc_type_keywords:
            if keyword in text_lower:
                main_category = keyword.capitalize()
                break
        
        if not main_category:
            # Fallback: extract first noun-like word
            words = text.split()
            for word in words:
                if len(word) > 3 and word[0].isupper():
                    main_category = word
                    break
        
        main_category = main_category or "Dokument"
        
        # 2. Extract context/sub-category
        sub_category = self._extract_subcategory(text, text_lower, main_category)
        
        # 3. Extract keywords (capitalized words, company names, etc.)
        keywords = self._extract_keywords(text)
        
        # 4. Build full name
        if sub_category:
            full_name = f"{main_category} ({sub_category})"
        else:
            full_name = main_category
        
        return {
            "main": main_category,
            "sub": sub_category,
            "full_name": full_name,
            "keywords": keywords,
            "source_text": text
        }
    
    def _extract_subcategory(self, text: str, text_lower: str, main_category: str) -> Optional[str]:
        """
        Extract sub-category from context.
        
        Examples:
            "Wartungsvertrag für Röntgengeräte" → "Medizingeräte"
            "Rechnung von Laborpartner" → "Labor"
        """
        # Common sub-category patterns
        sub_patterns = {
            "medizingeräte": ["röntgen", "ct", "ultraschall", "medizingerät"],
            "labor": ["labor", "dentlab", "zahnlabor"],
            "praxismöbel": ["stuhl", "möbel", "einrichtung"],
            "software": ["software", "lizenz", "abo"],
            "versicherung": ["versicherung", "police", "haftpflicht"],
            "mitarbeiter": ["mitarbeiter", "personal", "angestellte"],
        }
        
        for sub_name, patterns in sub_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return sub_name.capitalize()
        
        # Extract company names as sub-category
        # Pattern: "von XYZ" oder "für ABC"
        match = re.search(r'(?:von|für|bei)\s+([A-Z][a-zA-Z0-9\s&-]+)', text)
        if match:
            company = match.group(1).strip()
            # Clean up common words
            if company.lower() not in ["der", "die", "das", "ein", "eine"]:
                return company
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords (capitalized words, companies, technical terms).
        """
        keywords = []
        
        # Find capitalized words (likely nouns, names, companies)
        words = text.split()
        for i, word in enumerate(words):
            # Skip first word if it's capitalized (sentence start)
            if i == 0:
                continue
            
            # Capitalized word that's not after punctuation
            if word and word[0].isupper() and len(word) > 2:
                # Remove punctuation
                clean_word = re.sub(r'[^\w\s-]', '', word)
                if clean_word:
                    keywords.append(clean_word)
        
        # Find technical terms (e.g., "Röntgengeräte", "Zahnersatz")
        technical_terms = re.findall(r'\b[A-Z][a-zäöü]+(?:geräte?|anlage|system|vertrag|rechnung)\b', text)
        keywords.extend(technical_terms)
        
        # Deduplicate
        return list(set(keywords))
    
    def add_new_category(
        self,
        category_info: Dict,
        user_id: int,
        user_name: str
    ) -> Dict:
        """
        Fügt neue User-definierte Kategorie hinzu.
        
        Args:
            category_info: Result from extract_category_from_explanation()
            user_id: User who created this category
            user_name: User name for logging
        
        Returns:
            {
                "status": "created" | "merged" | "exists",
                "category": str,
                "message": str
            }
        """
        full_name = category_info["full_name"]
        
        # Check if similar category already exists
        similar = self.find_similar_category(full_name)
        
        if similar and similar["similarity"] >= 0.9:
            # Very similar → merge
            existing_cat = similar["category"]
            
            logger.info(
                f"[DynamicCategories] Merging '{full_name}' "
                f"into existing '{existing_cat['name']}' "
                f"(similarity: {similar['similarity']:.2%})"
            )
            
            # Update document count
            existing_cat["document_count"] += 1
            self._save_categories()
            
            return {
                "status": "merged",
                "category": existing_cat["name"],
                "message": f"Kategorie existiert bereits als '{existing_cat['name']}'"
            }
        
        # New category!
        new_category = {
            "name": full_name,
            "main": category_info["main"],
            "sub": category_info.get("sub"),
            "keywords": category_info["keywords"],
            "created_by": user_id,
            "created_by_name": user_name,
            "created_at": datetime.now().isoformat(),
            "document_count": 1
        }
        
        self.categories.append(new_category)
        self._save_categories()
        
        logger.info(
            f"[DynamicCategories] ✓ New category created: '{full_name}' "
            f"by {user_name} (total: {len(self.categories)})"
        )
        
        return {
            "status": "created",
            "category": full_name,
            "message": f"Neue Kategorie '{full_name}' erstellt!"
        }
    
    def find_similar_category(self, category_name: str) -> Optional[Dict]:
        """
        Findet ähnliche existierende Kategorien.
        
        Returns:
            {
                "category": Dict,
                "similarity": float (0.0-1.0)
            }
            or None if no similar category found
        """
        if not self.categories:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        for cat in self.categories:
            similarity = SequenceMatcher(None, category_name.lower(), cat["name"].lower()).ratio()
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = cat
        
        # Only return if similarity is significant
        if best_similarity >= 0.7:
            return {
                "category": best_match,
                "similarity": best_similarity
            }
        
        return None
    
    def get_all_categories(self, sort_by: str = "count") -> List[Dict]:
        """
        Gibt alle User-definierten Kategorien zurück.
        
        Args:
            sort_by: "count" (most used) | "name" (alphabetical) | "date" (newest first)
        
        Returns:
            List of category dicts
        """
        if sort_by == "count":
            return sorted(self.categories, key=lambda x: x["document_count"], reverse=True)
        elif sort_by == "name":
            return sorted(self.categories, key=lambda x: x["name"])
        elif sort_by == "date":
            return sorted(self.categories, key=lambda x: x["created_at"], reverse=True)
        else:
            return self.categories
    
    def increment_usage(self, category_name: str):
        """
        Erhöht Nutzungs-Counter für Kategorie.
        """
        for cat in self.categories:
            if cat["name"] == category_name:
                cat["document_count"] += 1
                self._save_categories()
                logger.debug(f"[DynamicCategories] {category_name}: {cat['document_count']} documents")
                return
        
        logger.warning(f"[DynamicCategories] Category not found for increment: {category_name}")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about category system.
        """
        if not self.categories:
            return {
                "total_categories": 0,
                "most_used": None,
                "least_used": None,
                "avg_docs_per_category": 0
            }
        
        sorted_by_usage = sorted(self.categories, key=lambda x: x["document_count"], reverse=True)
        total_docs = sum(cat["document_count"] for cat in self.categories)
        
        return {
            "total_categories": len(self.categories),
            "total_documents": total_docs,
            "most_used": sorted_by_usage[0],
            "least_used": sorted_by_usage[-1],
            "avg_docs_per_category": total_docs / len(self.categories)
        }
    
    def _load_categories(self):
        """Load categories from JSON file."""
        try:
            path = Path(self.categories_file)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
                logger.info(f"[DynamicCategories] Loaded {len(self.categories)} categories")
            else:
                logger.info("[DynamicCategories] No existing categories file, starting fresh")
                self.categories = []
        except Exception as e:
            logger.error(f"[DynamicCategories] Failed to load categories: {e}")
            self.categories = []
    
    def _save_categories(self):
        """Save categories to JSON file."""
        try:
            path = Path(self.categories_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"[DynamicCategories] Saved {len(self.categories)} categories")
        except Exception as e:
            logger.error(f"[DynamicCategories] Failed to save categories: {e}")


# Singleton instance
dynamic_categories = DynamicCategorySystem()
