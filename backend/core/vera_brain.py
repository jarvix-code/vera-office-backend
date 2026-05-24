"""
VERA Brain - Semantic Memory & Knowledge Graph
Copied from Javix Brain (projects/self-upgrade/src/brain_v2.py)
"""
from pathlib import Path
from typing import List, Dict, Optional
import json
import sqlite3
from datetime import datetime
from loguru import logger

# VERA Brain DB Path
VERA_BRAIN_DB = Path("C:/Jarvix/vera-office/data/vera_brain.db")


class VERABrain:
    """
    VERA's Brain System - Semantic Memory + Knowledge Graph
    
    Säulen:
    1. Facts - Fakten über die Praxis (Adresse, Team, Geräte, etc.)
    2. Documents - QM/ERP/Dokumente mit OCR-Text
    3. Compliance - QM-Anforderungen (erfüllt/offen)
    4. Learnings - Was VERA gelernt hat
    5. Context - Konversations-Kontext
    """
    
    def __init__(self):
        self.db_path = VERA_BRAIN_DB
        self._ensure_db()
    
    def _ensure_db(self):
        """Create brain tables if not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Facts Table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY,
                category TEXT,
                key TEXT,
                value TEXT,
                source TEXT,
                confidence REAL,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Documents Index (schneller Zugriff auf OCR-Texte)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_index (
                id INTEGER PRIMARY KEY,
                doc_type TEXT,
                doc_id INTEGER,
                title TEXT,
                ocr_preview TEXT,
                full_text TEXT,
                keywords TEXT,
                created_at TEXT
            )
        """)
        
        # Compliance Checklist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS compliance_items (
                id INTEGER PRIMARY KEY,
                chapter TEXT,
                requirement TEXT,
                status TEXT,
                evidence TEXT,
                last_check TEXT,
                notes TEXT
            )
        """)
        
        # Learnings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY,
                topic TEXT,
                insight TEXT,
                source TEXT,
                confidence REAL,
                created_at TEXT
            )
        """)
        
        # Context (Konversationen)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                user_message TEXT,
                vera_response TEXT,
                intent TEXT,
                entities TEXT,
                timestamp TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("[OK] VERA Brain initialized")
    
    def add_fact(self, category: str, key: str, value: str, source: str = "manual", confidence: float = 1.0):
        """Add or update a fact."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if exists
        cur.execute("SELECT id FROM facts WHERE category=? AND key=?", (category, key))
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE facts 
                SET value=?, source=?, confidence=?, updated_at=?
                WHERE id=?
            """, (value, source, confidence, now, existing[0]))
        else:
            cur.execute("""
                INSERT INTO facts (category, key, value, source, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (category, key, value, source, confidence, now, now))
        
        conn.commit()
        conn.close()
        
        logger.info(f" Fact added: {category}.{key} = {value[:50]}...")
    
    def search_facts(self, query: str) -> List[Dict]:
        """Search facts by query."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT category, key, value, source, confidence
            FROM facts
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY confidence DESC
            LIMIT 10
        """, (f"%{query}%", f"%{query}%"))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "category": row[0],
                "key": row[1],
                "value": row[2],
                "source": row[3],
                "confidence": row[4]
            })
        
        conn.close()
        return results
    
    def index_document(self, doc_type: str, doc_id: int, title: str, ocr_text: str):
        """Index a document for fast search."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Extract keywords (simple: first 20 unique words)
        words = set(ocr_text.lower().split()[:500])
        keywords = " ".join(list(words)[:20])
        
        cur.execute("""
            INSERT OR REPLACE INTO document_index 
            (doc_type, doc_id, title, ocr_preview, full_text, keywords, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_type,
            doc_id,
            title,
            ocr_text[:500],
            ocr_text[:10000],  # Max 10K for search
            keywords,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[DOC] Document indexed: {doc_type} #{doc_id} - {title}")
    
    def search_documents(self, query: str, doc_type: Optional[str] = None) -> List[Dict]:
        """Search documents by query."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        if doc_type:
            cur.execute("""
                SELECT doc_type, doc_id, title, ocr_preview
                FROM document_index
                WHERE doc_type=? AND (title LIKE ? OR full_text LIKE ? OR keywords LIKE ?)
                LIMIT 10
            """, (doc_type, f"%{query}%", f"%{query}%", f"%{query}%"))
        else:
            cur.execute("""
                SELECT doc_type, doc_id, title, ocr_preview
                FROM document_index
                WHERE title LIKE ? OR full_text LIKE ? OR keywords LIKE ?
                LIMIT 10
            """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "doc_type": row[0],
                "doc_id": row[1],
                "title": row[2],
                "preview": row[3]
            })
        
        conn.close()
        return results
    
    def get_compliance_status(self) -> Dict:
        """Get QM compliance summary."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("SELECT status, COUNT(*) FROM compliance_items GROUP BY status")
        
        status = {}
        for row in cur.fetchall():
            status[row[0]] = row[1]
        
        conn.close()
        
        return {
            "erfüllt": status.get("erfüllt", 0),
            "offen": status.get("offen", 0),
            "in_arbeit": status.get("in_arbeit", 0),
            "total": sum(status.values())
        }
    
    def add_learning(self, topic: str, insight: str, source: str = "conversation", confidence: float = 0.8):
        """Add a learning."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO learnings (topic, insight, source, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (topic, insight, source, confidence, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"[BRAIN] Learning added: {topic} - {insight[:50]}...")


# Global VERA Brain instance
vera_brain = VERABrain()
