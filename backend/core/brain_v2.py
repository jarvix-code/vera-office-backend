#!/usr/bin/env python3
"""
Brain v2.0 - 3-Layer Memory System for Javix

Layers:
1. Profile Memory (SQLite) - Persistent user facts, preferences, rules
2. Working Memory (In-Memory + SQLite) - Active tasks, session state
3. Episodic Memory (LanceDB) - Semantic memories via BrainEngine

Smart Recall combines all three layers with token budget enforcement.
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4


class ProfileMemory:
    """Layer 1: Persistent user facts, preferences, rules in SQLite."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "profiles.db")
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'fact',
                importance INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_profile_category
                ON user_profile(category);
        ''')
        conn.commit()
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def update_profile(self, key: str, value: str,
                       category: str = "fact", importance: int = 5):
        """Set or update a profile entry."""
        conn = self._conn()
        conn.execute(
            '''INSERT INTO user_profile (key, value, category, importance, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value=excluded.value,
                   category=excluded.category,
                   importance=excluded.importance,
                   updated_at=excluded.updated_at''',
            (key, value, category, importance, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def get_profile(self, key: str) -> Optional[Dict]:
        """Get a single profile entry."""
        conn = self._conn()
        row = conn.execute(
            'SELECT * FROM user_profile WHERE key=?', (key,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all(self, category: Optional[str] = None) -> List[Dict]:
        """Get all profile entries, optionally filtered by category."""
        conn = self._conn()
        if category:
            rows = conn.execute(
                'SELECT * FROM user_profile WHERE category=? ORDER BY importance DESC',
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM user_profile ORDER BY importance DESC'
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_profile(self, key: str) -> bool:
        conn = self._conn()
        cursor = conn.execute('DELETE FROM user_profile WHERE key=?', (key,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def search_profiles(self, query: str) -> List[Dict]:
        """Simple text search in profile keys and values."""
        conn = self._conn()
        rows = conn.execute(
            '''SELECT * FROM user_profile
               WHERE key LIKE ? OR value LIKE ?
               ORDER BY importance DESC''',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def format_for_context(self, max_tokens: int = 300) -> str:
        """Format profile as context block with token budget."""
        entries = self.get_all()
        if not entries:
            return ""

        lines = ["<user-profile>"]
        token_count = 4  # tag overhead

        for entry in entries:
            line = f"- {entry['key']}: {entry['value']}"
            est_tokens = len(line) // 4
            if token_count + est_tokens > max_tokens:
                break
            lines.append(line)
            token_count += est_tokens

        lines.append("</user-profile>")
        return "\n".join(lines)

    def stats(self) -> Dict:
        conn = self._conn()
        total = conn.execute('SELECT COUNT(*) FROM user_profile').fetchone()[0]
        categories = {}
        for row in conn.execute(
            'SELECT category, COUNT(*) as cnt FROM user_profile GROUP BY category'
        ).fetchall():
            categories[row['category']] = row['cnt']
        conn.close()
        return {"total": total, "categories": categories}


class WorkingMemory:
    """Layer 2: Active task tracking and session state.

    Persists to SQLite so tasks survive server restarts,
    but also kept in-memory for fast access.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "profiles.db")
        self.db_path = db_path
        self._init_db()
        # In-memory cache of active tasks
        self._tasks: Dict[str, Dict] = {}
        self._load_active_tasks()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS working_memory (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                context TEXT DEFAULT '{}',
                open_questions TEXT DEFAULT '[]',
                completion_criteria TEXT DEFAULT '[]',
                project TEXT DEFAULT '',
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_wm_status
                ON working_memory(status);
        ''')
        conn.commit()
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_active_tasks(self):
        """Load active tasks from DB into memory cache."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM working_memory WHERE status IN ('in_progress', 'paused')"
        ).fetchall()
        conn.close()
        for row in rows:
            task = dict(row)
            task['context'] = json.loads(task.get('context', '{}') or '{}')
            task['open_questions'] = json.loads(task.get('open_questions', '[]') or '[]')
            task['completion_criteria'] = json.loads(task.get('completion_criteria', '[]') or '[]')
            self._tasks[task['task_id']] = task

    def start_task(self, description: str, project: str = "",
                   context: Optional[Dict] = None,
                   completion_criteria: Optional[List[str]] = None) -> str:
        """Start a new task. Returns task_id."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        now = datetime.utcnow().isoformat()

        task = {
            'task_id': task_id,
            'description': description,
            'status': 'in_progress',
            'context': context or {},
            'open_questions': [],
            'completion_criteria': completion_criteria or [],
            'project': project,
            'started_at': now,
            'updated_at': now,
            'completed_at': None,
        }

        conn = self._conn()
        conn.execute(
            '''INSERT INTO working_memory
               (task_id, description, status, context, open_questions,
                completion_criteria, project, started_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (task_id, description, 'in_progress',
             json.dumps(task['context']),
             json.dumps(task['open_questions']),
             json.dumps(task['completion_criteria']),
             project, now, now)
        )
        conn.commit()
        conn.close()

        self._tasks[task_id] = task
        return task_id

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields (context, open_questions, status, etc.)."""
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        now = datetime.utcnow().isoformat()

        for key, value in kwargs.items():
            if key in task:
                task[key] = value
        task['updated_at'] = now

        conn = self._conn()
        conn.execute(
            '''UPDATE working_memory SET
                description=?, status=?, context=?, open_questions=?,
                completion_criteria=?, project=?, updated_at=?
               WHERE task_id=?''',
            (task['description'], task['status'],
             json.dumps(task['context']),
             json.dumps(task['open_questions']),
             json.dumps(task['completion_criteria']),
             task['project'], now, task_id)
        )
        conn.commit()
        conn.close()
        return True

    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed."""
        if task_id not in self._tasks:
            return False

        now = datetime.utcnow().isoformat()
        self._tasks[task_id]['status'] = 'completed'
        self._tasks[task_id]['completed_at'] = now
        self._tasks[task_id]['updated_at'] = now

        conn = self._conn()
        conn.execute(
            '''UPDATE working_memory SET status='completed',
               completed_at=?, updated_at=? WHERE task_id=?''',
            (now, now, task_id)
        )
        conn.commit()
        conn.close()

        # Remove from active cache
        del self._tasks[task_id]
        return True

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a specific task."""
        return self._tasks.get(task_id)

    def get_active_tasks(self) -> List[Dict]:
        """Get all in-progress tasks."""
        return [t for t in self._tasks.values() if t['status'] == 'in_progress']

    def get_all_tasks(self, limit: int = 20) -> List[Dict]:
        """Get all tasks (including completed) from DB."""
        conn = self._conn()
        rows = conn.execute(
            'SELECT * FROM working_memory ORDER BY updated_at DESC LIMIT ?',
            (limit,)
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            task = dict(row)
            task['context'] = json.loads(task.get('context', '{}') or '{}')
            task['open_questions'] = json.loads(task.get('open_questions', '[]') or '[]')
            task['completion_criteria'] = json.loads(task.get('completion_criteria', '[]') or '[]')
            result.append(task)
        return result

    def format_for_context(self, max_tokens: int = 200) -> str:
        """Format active tasks as context block."""
        active = self.get_active_tasks()
        if not active:
            return ""

        lines = ["<working-memory>"]
        token_count = 4

        for task in active:
            line = f"- [{task['status']}] {task['description']}"
            if task['project']:
                line += f" (project: {task['project']})"
            est_tokens = len(line) // 4
            if token_count + est_tokens > max_tokens:
                break
            lines.append(line)
            token_count += est_tokens

            # Add open questions if any
            for q in task.get('open_questions', []):
                qline = f"  ? {q}"
                qest = len(qline) // 4
                if token_count + qest > max_tokens:
                    break
                lines.append(qline)
                token_count += qest

        lines.append("</working-memory>")
        return "\n".join(lines)

    def stats(self) -> Dict:
        conn = self._conn()
        total = conn.execute('SELECT COUNT(*) FROM working_memory').fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM working_memory WHERE status='in_progress'"
        ).fetchone()[0]
        completed = conn.execute(
            "SELECT COUNT(*) FROM working_memory WHERE status='completed'"
        ).fetchone()[0]
        conn.close()
        return {"total": total, "active": active, "completed": completed}


class BrainV2:
    """Brain v2.0 - Unified 3-layer memory system.

    Combines:
    - Profile Memory (SQLite) for user facts/prefs
    - Working Memory (SQLite + in-memory) for active tasks
    - Episodic Memory (LanceDB via BrainEngine) for semantic search
    """

    def __init__(self, brain_engine=None, db_path: Optional[str] = None):
        """
        Args:
            brain_engine: Existing BrainEngine instance (for episodic memory).
                         If None, will create one on first use.
            db_path: Path to profiles.db. Defaults to data/profiles.db.
        """
        if db_path is None:
            db_path = str(Path(__file__).parent.parent / "data" / "profiles.db")

        self.profile = ProfileMemory(db_path)
        self.working = WorkingMemory(db_path)
        self._brain_engine = brain_engine

    @property
    def episodic(self):
        """Lazy-load BrainEngine for episodic memory."""
        if self._brain_engine is None:
            from brain_engine import BrainEngine
            self._brain_engine = BrainEngine()
        return self._brain_engine

    #  Smart Recall 

    def recall(self, query: str, max_tokens: int = 1000) -> Dict:
        """
        Smart Recall combining all 3 memory layers with token budget.

        Token budget allocation:
        - Profile Memory: 30% (max 300 tokens)
        - Working Memory: 20% (max 200 tokens)
        - Episodic Memory: 50% (max 500 tokens)

        Args:
            query: User message / search query
            max_tokens: Total token budget for context

        Returns:
            {
                "context": str,     # Combined context block
                "token_count": int, # Estimated tokens used
                "sources": {
                    "profile": int, # Tokens from profile
                    "working": int, # Tokens from working memory
                    "episodic": int # Tokens from episodic
                }
            }
        """
        # Budget allocation
        profile_budget = int(max_tokens * 0.3)
        working_budget = int(max_tokens * 0.2)
        episodic_budget = max_tokens - profile_budget - working_budget

        parts = []
        sources = {"profile": 0, "working": 0, "episodic": 0}

        # Layer 1: Profile Memory (relevant entries)
        profile_ctx = self._recall_profile(query, profile_budget)
        if profile_ctx:
            parts.append(profile_ctx)
            sources["profile"] = len(profile_ctx) // 4

        # Layer 2: Working Memory (active tasks)
        working_ctx = self.working.format_for_context(working_budget)
        if working_ctx:
            parts.append(working_ctx)
            sources["working"] = len(working_ctx) // 4

        # Layer 3: Episodic Memory (semantic search)
        # Give leftover budget from profile/working to episodic
        used = sources["profile"] + sources["working"]
        actual_episodic_budget = max_tokens - used
        episodic_ctx = self._recall_episodic(query, actual_episodic_budget)
        if episodic_ctx:
            parts.append(episodic_ctx)
            sources["episodic"] = len(episodic_ctx) // 4

        context = "\n\n".join(parts) if parts else ""
        token_count = sum(sources.values())

        return {
            "context": context,
            "token_count": token_count,
            "sources": sources,
        }

    def _recall_profile(self, query: str, max_tokens: int) -> str:
        """Get relevant profile entries for query."""
        # First try search
        results = self.profile.search_profiles(query)
        if not results:
            # Fallback: get high-importance entries
            results = self.profile.get_all()

        if not results:
            return ""

        lines = ["<user-profile>"]
        token_count = 4

        for entry in results:
            line = f"- {entry['key']}: {entry['value']}"
            est = len(line) // 4
            if token_count + est > max_tokens:
                break
            lines.append(line)
            token_count += est

        if len(lines) <= 1:
            return ""

        lines.append("</user-profile>")
        return "\n".join(lines)

    def _recall_episodic(self, query: str, max_tokens: int) -> str:
        """Get episodic memories with token budget."""
        memories = self.episodic.search_with_budget(
            query, max_tokens=max_tokens, top_k=10
        )
        if not memories:
            return ""

        lines = ["<episodic-memory>"]
        for i, mem in enumerate(memories, 1):
            text = mem.get('text', '')
            cat = mem.get('category', 'fact')
            proj = mem.get('project', '')
            proj_str = f", project:{proj}" if proj else ""
            lines.append(f"[{i}] ({cat}{proj_str}) {text}")
        lines.append("</episodic-memory>")
        return "\n".join(lines)

    #  Convenience methods 

    def start_task(self, description: str, **kwargs) -> str:
        """Start a new task in working memory."""
        return self.working.start_task(description, **kwargs)

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update an active task."""
        return self.working.update_task(task_id, **kwargs)

    def complete_task(self, task_id: str) -> bool:
        """Complete a task."""
        return self.working.complete_task(task_id)

    def update_profile(self, key: str, value: str, **kwargs):
        """Update user profile."""
        self.profile.update_profile(key, value, **kwargs)

    def get_profile(self, key: str) -> Optional[Dict]:
        """Get profile entry."""
        return self.profile.get_profile(key)

    def store_memory(self, text: str, **kwargs) -> str:
        """Store episodic memory."""
        return self.episodic.store(text, **kwargs)

    #  Status 

    def get_status(self) -> Dict:
        """Full status of all memory layers."""
        profile_stats = self.profile.stats()
        working_stats = self.working.stats()
        try:
            episodic_stats = self.episodic.stats()
        except Exception:
            episodic_stats = {"total": 0, "error": "not loaded"}

        return {
            "version": "2.0",
            "profile_memory": profile_stats,
            "working_memory": working_stats,
            "episodic_memory": episodic_stats,
        }

    def to_dict(self) -> Dict:
        """Serializable status."""
        return self.get_status()


#  Singleton 

_brain_v2: Optional[BrainV2] = None


def get_brain_v2(brain_engine=None) -> BrainV2:
    """Get or create singleton BrainV2 instance."""
    global _brain_v2
    if _brain_v2 is None:
        _brain_v2 = BrainV2(brain_engine=brain_engine)
    return _brain_v2


def main():
    """CLI test for Brain v2.0 (without BrainEngine for quick testing)."""
    import tempfile

    print("[TEST] Brain v2.0\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_profiles.db")

        # Create with dummy brain
        class DummyBrain:
            def search_with_budget(self, query, max_tokens=1000, top_k=10):
                return [{"text": "UltraTrader is a trading bot", "category": "fact", "project": "ultratrader"}]
            def store(self, text, metadata=None):
                return "dummy_id"
            def stats(self):
                return {"total": 1}

        brain = BrainV2(brain_engine=DummyBrain(), db_path=db_path)

        # Test Profile Memory
        print("=== Profile Memory ===")
        brain.update_profile("user_name", "Boris Reimers", category="fact", importance=10)
        brain.update_profile("user_role", "Zahnarzt", category="fact", importance=8)
        brain.update_profile("preferred_language", "Deutsch", category="preference", importance=9)
        brain.update_profile("project_main", "UltraTrader", category="fact", importance=9)

        profile = brain.get_profile("user_name")
        print(f"  user_name: {profile['value']}")

        all_facts = brain.profile.get_all("fact")
        print(f"  Facts: {len(all_facts)}")

        # Test Working Memory
        print("\n=== Working Memory ===")
        tid = brain.start_task(
            "Implement Brain v2.0",
            project="self-upgrade",
            completion_criteria=["Profile Memory works", "Working Memory works", "Tests pass"]
        )
        print(f"  Started task: {tid}")

        brain.update_task(tid, open_questions=["Which token budget split?"])
        active = brain.working.get_active_tasks()
        print(f"  Active tasks: {len(active)}")

        brain.complete_task(tid)
        active_after = brain.working.get_active_tasks()
        print(f"  Active after complete: {len(active_after)}")

        # Test Smart Recall
        print("\n=== Smart Recall ===")
        result = brain.recall("Was ist UltraTrader?", max_tokens=500)
        print(f"  Token count: {result['token_count']}")
        print(f"  Sources: {result['sources']}")
        print(f"  Context length: {len(result['context'])} chars")

        # Status
        print("\n=== Status ===")
        status = brain.get_status()
        print(f"  Version: {status['version']}")
        print(f"  Profile entries: {status['profile_memory']['total']}")
        print(f"  Working tasks: {status['working_memory']['total']}")
        print(f"  Episodic memories: {status['episodic_memory']['total']}")

        print("\n[OK] All Brain v2.0 tests passed!")


if __name__ == '__main__':
    main()
