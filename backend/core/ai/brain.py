"""
VERA Brain — SQLite-basiertes Lerngedächtnis

VERA lernt aus jeder Interaktion:
- Dokumenten-Klassifizierungen (richtig/falsch)
- User-Korrekturen → nächstes Mal besser
- Erkannte Muster (Absender → Kategorie)
- Domänenwissen (branchenspezifisch)
- Konversations-Erinnerungen (User-Präferenzen)

Je länger VERA läuft, desto besser wird sie.
"""
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.config import config

logger = logging.getLogger(__name__)

BRAIN_DB_PATH = config.DATA_DIR / "brain.db"


class VERABrain:
    """VERAs Langzeitgedächtnis — lernt aus jeder Interaktion."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()
        logger.info(f"🧠 VERA Brain initialisiert: {BRAIN_DB_PATH}")
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(BRAIN_DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def _init_db(self):
        """Erstellt alle Brain-Tabellen."""
        conn = self._get_conn()
        conn.executescript("""
            -- Gelernte Klassifizierungen: Was VERA über Dokumente gelernt hat
            CREATE TABLE IF NOT EXISTS learned_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,       -- 'sender', 'keyword', 'layout', 'filename'
                pattern_value TEXT NOT NULL,       -- z.B. "AOK Bayern", "Gehaltsabrechnung", "RE-*"
                category TEXT NOT NULL,            -- Ziel-Kategorie
                confidence REAL DEFAULT 0.5,       -- 0.0-1.0, steigt mit Bestätigungen
                times_seen INTEGER DEFAULT 1,      -- Wie oft gesehen
                times_confirmed INTEGER DEFAULT 0, -- Wie oft bestätigt
                times_corrected INTEGER DEFAULT 0, -- Wie oft korrigiert
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(pattern_type, pattern_value, category)
            );

            -- User-Korrekturen: Explizites Feedback
            CREATE TABLE IF NOT EXISTS corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                original_category TEXT,
                corrected_category TEXT NOT NULL,
                original_name TEXT,
                corrected_name TEXT,
                reason TEXT,                       -- Warum korrigiert
                created_at TEXT NOT NULL
            );

            -- Absender-Mapping: Absender → Kategorie (häufigstes Muster)
            CREATE TABLE IF NOT EXISTS sender_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL UNIQUE,        -- Erkannter Absender
                typical_category TEXT NOT NULL,     -- Häufigste Kategorie
                typical_doc_type TEXT,              -- z.B. "Rechnung", "Mahnung"
                count INTEGER DEFAULT 1,
                last_seen TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Domänenwissen: Branchenspezifisches Wissen
            CREATE TABLE IF NOT EXISTS domain_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,               -- z.B. "aufbewahrungsfrist", "dokumenttyp"
                key TEXT NOT NULL,                 -- z.B. "lohnabrechnung", "rechnung"
                value TEXT NOT NULL,               -- JSON oder Text
                source TEXT DEFAULT 'system',      -- 'system', 'user', 'learned'
                created_at TEXT NOT NULL,
                UNIQUE(topic, key)
            );

            -- Konversations-Erinnerungen: Was VERA über den User weiß
            CREATE TABLE IF NOT EXISTS user_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,           -- z.B. "preferred_name", "doc_naming_style"
                value TEXT NOT NULL,
                learned_from TEXT,                  -- Kontext wo gelernt
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Lern-Log: Nachvollziehbar was VERA wann gelernt hat
            CREATE TABLE IF NOT EXISTS learning_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,           -- 'classification', 'correction', 'pattern', 'feedback'
                description TEXT NOT NULL,
                data TEXT,                          -- JSON mit Details
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_lc_pattern ON learned_classifications(pattern_type, pattern_value);
            CREATE INDEX IF NOT EXISTS idx_lc_category ON learned_classifications(category);
            CREATE INDEX IF NOT EXISTS idx_sender ON sender_map(sender);
            CREATE INDEX IF NOT EXISTS idx_domain ON domain_knowledge(topic, key);
            CREATE INDEX IF NOT EXISTS idx_log_type ON learning_log(event_type);
        """)
        conn.commit()
        conn.close()
    
    # ============================================================
    # Klassifizierungs-Lernen
    # ============================================================
    
    def learn_classification(self, pattern_type: str, pattern_value: str, 
                              category: str, confirmed: bool = False):
        """
        Lerne aus einer Klassifizierung.
        
        Args:
            pattern_type: 'sender', 'keyword', 'layout', 'filename'
            pattern_value: Der erkannte Wert
            category: Die Ziel-Kategorie
            confirmed: True wenn vom User bestätigt
        """
        conn = self._get_conn()
        now = datetime.now().isoformat()
        
        existing = conn.execute(
            "SELECT id, times_seen, times_confirmed, confidence FROM learned_classifications "
            "WHERE pattern_type=? AND pattern_value=? AND category=?",
            (pattern_type, pattern_value, category)
        ).fetchone()
        
        if existing:
            new_seen = existing["times_seen"] + 1
            new_confirmed = existing["times_confirmed"] + (1 if confirmed else 0)
            # Confidence steigt mit Bestätigungen, fällt nie unter 0.1
            new_confidence = min(0.99, max(0.1, new_confirmed / new_seen))
            
            conn.execute(
                "UPDATE learned_classifications SET times_seen=?, times_confirmed=?, "
                "confidence=?, updated_at=? WHERE id=?",
                (new_seen, new_confirmed, new_confidence, now, existing["id"])
            )
        else:
            confidence = 0.7 if confirmed else 0.3
            conn.execute(
                "INSERT INTO learned_classifications "
                "(pattern_type, pattern_value, category, confidence, times_seen, times_confirmed, created_at, updated_at) "
                "VALUES (?,?,?,?,1,?,?,?)",
                (pattern_type, pattern_value, category, confidence, 1 if confirmed else 0, now, now)
            )
        
        conn.commit()
        
        self._log_learning("classification", 
                          f"{'Bestätigt' if confirmed else 'Gesehen'}: {pattern_type}='{pattern_value}' → {category}",
                          {"pattern_type": pattern_type, "pattern_value": pattern_value, 
                           "category": category, "confirmed": confirmed})
        conn.close()
    
    def get_classification_hint(self, pattern_type: str, pattern_value: str, 
                                 min_confidence: float = 0.5) -> Optional[Dict]:
        """
        Frage VERA: Welche Kategorie passt zu diesem Muster?
        
        Returns:
            Dict mit {category, confidence} oder None
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT category, confidence, times_seen, times_confirmed "
            "FROM learned_classifications "
            "WHERE pattern_type=? AND pattern_value=? AND confidence>=? "
            "ORDER BY confidence DESC LIMIT 1",
            (pattern_type, pattern_value, min_confidence)
        ).fetchone()
        conn.close()
        
        if row:
            return {
                "category": row["category"],
                "confidence": row["confidence"],
                "times_seen": row["times_seen"],
                "times_confirmed": row["times_confirmed"]
            }
        return None
    
    def get_all_hints_for_document(self, sender: str = None, keywords: List[str] = None,
                                    filename: str = None) -> List[Dict]:
        """
        Sammle alle Hinweise für ein Dokument aus verschiedenen Quellen.
        
        Returns:
            Liste von Hints, nach Confidence sortiert
        """
        hints = []
        
        if sender:
            hint = self.get_classification_hint("sender", sender.lower())
            if hint:
                hint["source"] = "sender"
                hints.append(hint)
        
        if keywords:
            for kw in keywords:
                hint = self.get_classification_hint("keyword", kw.lower())
                if hint:
                    hint["source"] = f"keyword:{kw}"
                    hints.append(hint)
        
        if filename:
            hint = self.get_classification_hint("filename", filename.lower())
            if hint:
                hint["source"] = "filename"
                hints.append(hint)
            
            # Auch Prefix-Match versuchen
            prefix = filename.split("-")[0].split("_")[0].lower() if "-" in filename or "_" in filename else None
            if prefix and prefix != filename.lower():
                hint = self.get_classification_hint("filename", prefix)
                if hint:
                    hint["source"] = f"filename_prefix:{prefix}"
                    hints.append(hint)
        
        # Nach Confidence sortieren
        hints.sort(key=lambda h: h["confidence"], reverse=True)
        return hints
    
    # ============================================================
    # Korrekturen
    # ============================================================
    
    def record_correction(self, document_id: str, original_category: str,
                           corrected_category: str, original_name: str = None,
                           corrected_name: str = None, reason: str = None):
        """
        User hat eine Klassifizierung korrigiert → VERA lernt daraus.
        """
        conn = self._get_conn()
        now = datetime.now().isoformat()
        
        conn.execute(
            "INSERT INTO corrections "
            "(document_id, original_category, corrected_category, original_name, corrected_name, reason, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (document_id, original_category, corrected_category, original_name, corrected_name, reason, now)
        )
        
        # Confidence der falschen Klassifizierung senken
        conn.execute(
            "UPDATE learned_classifications SET times_corrected = times_corrected + 1, "
            "confidence = MAX(0.1, confidence - 0.1), updated_at=? "
            "WHERE category=? AND confidence > 0.1",
            (now, original_category)
        )
        
        conn.commit()
        conn.close()
        
        self._log_learning("correction",
                          f"Korrektur: '{original_category}' → '{corrected_category}'",
                          {"document_id": document_id, "from": original_category, 
                           "to": corrected_category, "reason": reason})
        
        logger.info(f"🧠 Korrektur gelernt: {original_category} → {corrected_category}")
    
    # ============================================================
    # Absender-Mapping
    # ============================================================
    
    def learn_sender(self, sender: str, category: str, doc_type: str = None):
        """Lerne: Dieser Absender schickt üblicherweise diese Art Dokument."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        
        existing = conn.execute(
            "SELECT id, count FROM sender_map WHERE sender=?", (sender.lower(),)
        ).fetchone()
        
        if existing:
            conn.execute(
                "UPDATE sender_map SET typical_category=?, typical_doc_type=?, "
                "count=count+1, last_seen=? WHERE id=?",
                (category, doc_type, now, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO sender_map (sender, typical_category, typical_doc_type, count, last_seen, created_at) "
                "VALUES (?,?,?,1,?,?)",
                (sender.lower(), category, doc_type, now, now)
            )
        
        conn.commit()
        conn.close()
    
    def get_sender_info(self, sender: str) -> Optional[Dict]:
        """Was weiß VERA über diesen Absender?"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM sender_map WHERE sender=?", (sender.lower(),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    
    # ============================================================
    # User Memory
    # ============================================================
    
    def remember(self, key: str, value: str, context: str = None):
        """VERA merkt sich etwas über den User."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO user_memory (key, value, learned_from, created_at, updated_at) "
            "VALUES (?,?,?,COALESCE((SELECT created_at FROM user_memory WHERE key=?),?),?)",
            (key, value, context, key, now, now)
        )
        conn.commit()
        conn.close()
        logger.debug(f"🧠 Gemerkt: {key}={value}")
    
    def recall(self, key: str) -> Optional[str]:
        """VERA erinnert sich."""
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM user_memory WHERE key=?", (key,)).fetchone()
        conn.close()
        return row["value"] if row else None
    
    def recall_all(self) -> Dict[str, str]:
        """Alles was VERA über den User weiß."""
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM user_memory").fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}
    
    # ============================================================
    # Domänenwissen
    # ============================================================
    
    def add_knowledge(self, topic: str, key: str, value: Any, source: str = "system"):
        """Füge Domänenwissen hinzu."""
        conn = self._get_conn()
        now = datetime.now().isoformat()
        val = json.dumps(value) if not isinstance(value, str) else value
        conn.execute(
            "INSERT OR REPLACE INTO domain_knowledge (topic, key, value, source, created_at) "
            "VALUES (?,?,?,?,?)",
            (topic, key, val, source, now)
        )
        conn.commit()
        conn.close()
    
    def get_knowledge(self, topic: str, key: str = None) -> Any:
        """Rufe Domänenwissen ab."""
        conn = self._get_conn()
        if key:
            row = conn.execute(
                "SELECT value FROM domain_knowledge WHERE topic=? AND key=?", (topic, key)
            ).fetchone()
            conn.close()
            if row:
                try:
                    return json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    return row["value"]
            return None
        else:
            rows = conn.execute(
                "SELECT key, value FROM domain_knowledge WHERE topic=?", (topic,)
            ).fetchall()
            conn.close()
            result = {}
            for r in rows:
                try:
                    result[r["key"]] = json.loads(r["value"])
                except (json.JSONDecodeError, TypeError):
                    result[r["key"]] = r["value"]
            return result
    
    # ============================================================
    # Lern-Log
    # ============================================================
    
    def _log_learning(self, event_type: str, description: str, data: Dict = None):
        """Logge was VERA gelernt hat (nachvollziehbar!)."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO learning_log (event_type, description, data, created_at) VALUES (?,?,?,?)",
            (event_type, description, json.dumps(data) if data else None, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    # ============================================================
    # Stats
    # ============================================================
    
    def get_stats(self) -> Dict:
        """Wie schlau ist VERA?"""
        conn = self._get_conn()
        stats = {
            "classifications_learned": conn.execute(
                "SELECT COUNT(*) as c FROM learned_classifications").fetchone()["c"],
            "high_confidence": conn.execute(
                "SELECT COUNT(*) as c FROM learned_classifications WHERE confidence >= 0.8").fetchone()["c"],
            "corrections_received": conn.execute(
                "SELECT COUNT(*) as c FROM corrections").fetchone()["c"],
            "senders_known": conn.execute(
                "SELECT COUNT(*) as c FROM sender_map").fetchone()["c"],
            "domain_facts": conn.execute(
                "SELECT COUNT(*) as c FROM domain_knowledge").fetchone()["c"],
            "user_memories": conn.execute(
                "SELECT COUNT(*) as c FROM user_memory").fetchone()["c"],
            "total_learnings": conn.execute(
                "SELECT COUNT(*) as c FROM learning_log").fetchone()["c"],
        }
        conn.close()
        return stats
    
    def seed_domain_knowledge(self):
        """
        Initialisiert umfassendes Domänenwissen für deutsche KMUs.
        Inkl. Zahnarztpraxis-Spezifika, Handwerk, Gastronomie, IT, GoBD, DSGVO.
        """
        from backend.core.ai.training_data import (
            RETENTION_PERIODS, SENDER_MAPPINGS, KEYWORD_PATTERNS,
            NAMING_RULES, DENTAL_KNOWLEDGE, HANDWERK_KNOWLEDGE,
            GASTRO_KNOWLEDGE, IT_KNOWLEDGE
        )
        
        # 1. Aufbewahrungsfristen (150+ Eintraege, GoBD-konform, branchenubergreifend)
        for key, val in RETENTION_PERIODS.items():
            self.add_knowledge("aufbewahrungsfrist", key, val, source="system")
        
        # 2. Absender → Kategorie (200+ Mappings)
        for sender, info in SENDER_MAPPINGS.items():
            self.add_knowledge("sender_hint", sender, info, source="system")
            # Auch direkt als Classification-Hint lernen
            self.learn_classification("sender", sender, info["category"], confirmed=True)
        
        # 3. Keyword-Patterns
        for name, pattern in KEYWORD_PATTERNS.items():
            self.add_knowledge("keyword_pattern", name, pattern, source="system")
            # Top-Keywords als Classification-Hints
            for kw in pattern["keywords"][:3]:
                self.learn_classification("keyword", kw, pattern["category"], confirmed=True)
        
        # 4. Benennungsregeln
        for doc_type, template in NAMING_RULES.items():
            self.add_knowledge("naming_rule", doc_type, template, source="system")
        
        # 5. Zahnarztpraxis-Wissen (GOZ, BEMA, Dokumentationspflichten)
        for topic, entries in DENTAL_KNOWLEDGE.items():
            for key, val in entries.items():
                self.add_knowledge(f"dental_{topic}", key, val, source="system")
        
        # 6. Handwerk-Wissen
        for topic, entries in HANDWERK_KNOWLEDGE.items():
            for key, val in entries.items():
                self.add_knowledge(f"handwerk_{topic}", key, val, source="system")
        
        # 7. Gastronomie-Wissen (HACCP, IfSG, LMHV)
        for topic, entries in GASTRO_KNOWLEDGE.items():
            for key, val in entries.items():
                self.add_knowledge(f"gastro_{topic}", key, val, source="system")
        
        # 8. IT-Branche-Wissen (DSGVO, ISO 27001)
        for topic, entries in IT_KNOWLEDGE.items():
            for key, val in entries.items():
                self.add_knowledge(f"it_{topic}", key, val, source="system")
        
        stats = self.get_stats()
        self._log_learning("seed", 
            f"Domänenwissen geladen: {len(RETENTION_PERIODS)} Fristen, "
            f"{len(SENDER_MAPPINGS)} Absender, {len(KEYWORD_PATTERNS)} Patterns, "
            f"{len(DENTAL_KNOWLEDGE)} Dental-Kategorien")
        logger.info(
            f"🧠 VERA Brain geseedet: {stats['classifications_learned']} Klassifizierungen, "
            f"{stats['domain_facts']} Fakten, {stats['senders_known']} Absender"
        )


# Global instance
brain = VERABrain()
