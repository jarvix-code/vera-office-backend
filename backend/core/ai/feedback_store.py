"""
Feedback Store - Stores user confirmations/corrections for continuous learning.
Uses TF-IDF for finding similar examples (few-shot learning).
"""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class FeedbackStore:
    """Storage for classification feedback with similarity search."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize feedback store."""
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "vera.db"
        
        self.db_path = str(db_path)
        self._ensure_table()
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
        self._corpus = []
        self._feedback_cache = []
        self._reload_cache()
    
    def _ensure_table(self):
        """Create feedback table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ocr_snippet TEXT NOT NULL,
                    category TEXT NOT NULL,
                    confirmed_by_user BOOLEAN DEFAULT 0,
                    auto_confirmed BOOLEAN DEFAULT 0,
                    confidence REAL,
                    weight REAL DEFAULT 1.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_category ON feedback(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)")
    
    def _reload_cache(self):
        """Reload all feedback into memory for TF-IDF."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, ocr_snippet, category, confirmed_by_user, 
                       auto_confirmed, confidence, weight
                FROM feedback
                ORDER BY timestamp DESC
            """)
            
            self._feedback_cache = []
            self._corpus = []
            
            for row in cursor.fetchall():
                feedback = {
                    'id': row[0],
                    'ocr_snippet': row[1],
                    'category': row[2],
                    'confirmed_by_user': bool(row[3]),
                    'auto_confirmed': bool(row[4]),
                    'confidence': row[5],
                    'weight': row[6]
                }
                self._feedback_cache.append(feedback)
                self._corpus.append(row[1])  # OCR text for vectorization
        
        # Fit vectorizer if we have data
        if self._corpus:
            try:
                self.vectorizer.fit(self._corpus)
            except Exception as e:
                logger.warning(f"Failed to fit TF-IDF vectorizer: {e}")
    
    def add_feedback(
        self,
        ocr_text: str,
        category: str,
        confirmed_by_user: bool = False,
        auto_confirmed: bool = False,
        confidence: Optional[float] = None
    ):
        """
        Add feedback entry.
        
        Args:
            ocr_text: OCR text snippet (first 1000 chars recommended)
            category: Correct category
            confirmed_by_user: True if user manually confirmed/corrected
            auto_confirmed: True if auto-filed with high confidence
            confidence: Classification confidence
        """
        # User corrections get higher weight
        weight = 2.0 if confirmed_by_user else 1.0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO feedback 
                (ocr_snippet, category, confirmed_by_user, auto_confirmed, confidence, weight)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ocr_text[:2000], category, confirmed_by_user, auto_confirmed, confidence, weight))
        
        # Reload cache to include new feedback
        self._reload_cache()
        
        logger.info(f"Feedback added: category={category}, user_confirmed={confirmed_by_user}")
    
    def get_similar_examples(self, ocr_text: str, n: int = 5) -> List[Dict]:
        """
        Find N most similar examples using TF-IDF cosine similarity.
        
        Args:
            ocr_text: OCR text to find similar examples for
            n: Number of examples to return
        
        Returns:
            List of feedback dictionaries with similarity scores
        """
        if not self._corpus:
            return []
        
        try:
            # Vectorize query text
            query_vec = self.vectorizer.transform([ocr_text])
            
            # Vectorize corpus
            corpus_vecs = self.vectorizer.transform(self._corpus)
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vec, corpus_vecs)[0]
            
            # Get top N indices (weighted by feedback weight)
            weighted_scores = []
            for idx, sim in enumerate(similarities):
                weight = self._feedback_cache[idx]['weight']
                weighted_scores.append((idx, sim * weight))
            
            # Sort by weighted similarity
            weighted_scores.sort(key=lambda x: x[1], reverse=True)
            top_indices = [idx for idx, _ in weighted_scores[:n]]
            
            # Return top examples with similarity scores
            results = []
            for idx in top_indices:
                example = self._feedback_cache[idx].copy()
                example['similarity'] = similarities[idx]
                results.append(example)
            
            return results
        
        except Exception as e:
            logger.error(f"Failed to find similar examples: {e}")
            return []
    
    def get_category_stats(self) -> Dict[str, int]:
        """Get number of confirmed examples per category."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM feedback
                WHERE confirmed_by_user = 1 OR auto_confirmed = 1
                GROUP BY category
            """)
            
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_total_feedback_count(self) -> int:
        """Get total number of feedback entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM feedback")
            return cursor.fetchone()[0]


# Global instance
feedback_store = FeedbackStore()
