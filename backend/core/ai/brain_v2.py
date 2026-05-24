"""
Brain v2 - Semantic Memory Engine
Hybrid search: FTS5 (keyword) + embeddings (semantic) + knowledge graph
"""
import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from sentence_transformers import SentenceTransformer

class BrainV2:
    def __init__(self, db_path: Optional[str] = None, table_name: str = "memories"):
        """Initialize Brain v2 with database and embedding model"""
        if db_path is None:
            workspace = Path(__file__).parent.parent.parent
            db_path = workspace / "memory.db"
        
        self.db_path = str(db_path)
        self.table_name = table_name
        self.fts_table = f"{table_name}_fts"
        
        self.db = sqlite3.connect(self.db_path)
        self.db.row_factory = sqlite3.Row
        
        print("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Brain v2 initialized")
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Tuple[int, float, dict]]:
        """
        Hybrid search combining FTS5 and semantic similarity
        Returns: [(memory_id, score, memory_dict), ...]
        """
        results = {}
        
        # 1. FTS5 keyword search
        try:
            # Escape FTS5 special chars and quote
            fts_query = '"%s"' % query.replace('"', '""')
            
            fts_cursor = self.db.execute(f"""
                SELECT m.id, m.event_type, m.description, m.data, m.created_at
                FROM {self.fts_table} f
                JOIN {self.table_name} m ON f.rowid = m.id
                WHERE {self.fts_table} MATCH ?
                LIMIT ?
            """, (fts_query, top_k * 2))
            
            for row in fts_cursor:
                mid = row['id']
                results[mid] = {
                    'id': mid,
                    'event_type': row['event_type'],
                    'description': row['description'],
                    'data': row['data'],
                    'created_at': row['created_at'],
                    'fts_score': 1.0,
                    'semantic_score': 0.0
                }
        except Exception as e:
            print(f"FTS5 search warning: {e}")
        
        # 2. Semantic search via embeddings
        try:
            q_emb = self.embedder.encode(query)
            
            emb_cursor = self.db.execute(f"""
                SELECT id, event_type, description, data, created_at, embedding 
                FROM {self.table_name}
                WHERE embedding IS NOT NULL
            """)
            
            for row in emb_cursor:
                mid = row['id']
                emb_bytes = row['embedding']
                
                if emb_bytes:
                    emb = np.frombuffer(emb_bytes, dtype=np.float32)
                    score = np.dot(q_emb, emb) / (np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-8)
                    
                    if score > 0.3:  # Threshold
                        if mid in results:
                            results[mid]['semantic_score'] = float(score)
                        else:
                            results[mid] = {
                                'id': mid,
                                'event_type': row['event_type'],
                                'description': row['description'],
                                'data': row['data'],
                                'created_at': row['created_at'],
                                'fts_score': 0.0,
                                'semantic_score': float(score)
                            }
        except Exception as e:
            print(f"Semantic search warning: {e}")
        
        # 3. Combine scores (weighted)
        ranked = []
        for mid, data in results.items():
            combined_score = (data['fts_score'] * 0.4) + (data['semantic_score'] * 0.6)
            ranked.append((mid, combined_score, data))
        
        # Sort by combined score
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked[:top_k]
    
    def store(self, event_type: str, description: str, data: str = None) -> int:
        """
        Store a new learning log entry with embedding
        Returns: log_id
        """
        try:
            # Generate embedding from description + data
            text = description + (' ' + data if data else '')
            emb = self.embedder.encode(text)
            
            cursor = self.db.execute(f"""
                INSERT INTO {self.table_name} (event_type, description, data, embedding, created_at, confidence, lifecycle)
                VALUES (?, ?, ?, ?, datetime('now'), 1.0, 'fresh')
            """, (event_type, description, data, emb.tobytes()))
            
            self.db.commit()
            log_id = cursor.lastrowid
            print(f"✅ Stored learning #{log_id}: {description}")
            return log_id
            
        except Exception as e:
            print(f"❌ Learning store failed: {e}")
            self.db.rollback()
            raise
    
    def add_relation(self, subject_id: int, predicate: str, object_id: int) -> None:
        """
        Add/strengthen a knowledge graph relation
        """
        try:
            self.db.execute("""
                INSERT INTO knowledge_graph (subject_id, predicate, object_id, strength)
                VALUES (?, ?, ?, 1.0)
                ON CONFLICT(subject_id, predicate, object_id) 
                DO UPDATE SET 
                    strength = strength + 0.1,
                    last_accessed = datetime('now')
            """, (subject_id, predicate, object_id))
            
            self.db.commit()
            print(f"✅ Relation added: {subject_id} -{predicate}-> {object_id}")
            
        except Exception as e:
            print(f"❌ Relation failed: {e}")
            self.db.rollback()
            raise
    
    def get_related(self, memory_id: int, limit: int = 5) -> List[dict]:
        """
        Get related memories via knowledge graph (both directions)
        """
        try:
            # Query both subject_id and object_id to get bidirectional relations
            cursor = self.db.execute("""
                SELECT 
                    kg.predicate,
                    kg.strength,
                    m.id, m.category, m.title, m.content
                FROM knowledge_graph kg
                JOIN memories m ON (kg.object_id = m.id OR kg.subject_id = m.id)
                WHERE (kg.subject_id = ? OR kg.object_id = ?) AND m.id != ?
                ORDER BY kg.strength DESC, kg.last_accessed DESC
                LIMIT ?
            """, (memory_id, memory_id, memory_id, limit))
            
            related = []
            for row in cursor:
                related.append({
                    'predicate': row['predicate'],
                    'strength': row['strength'],
                    'memory': {
                        'id': row['id'],
                        'category': row['category'],
                        'title': row['title'],
                        'content': row['content']
                    }
                })
            
            return related
            
        except Exception as e:
            print(f"❌ Get related failed: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        self.db.close()


if __name__ == "__main__":
    print("Brain v2 Engine - Ready for import")
