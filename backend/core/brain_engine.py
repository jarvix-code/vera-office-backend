#!/usr/bin/env python3
"""
Brain Engine - Semantic Memory System for Javix
Phase 1 des Self-Upgrade Projekts

Features:
- Lokales Embedding via sentence-transformers (nomic-embed-text-v1.5)
- LanceDB als Vektor-Store
- BM25 für Keyword-Suche
- Hybrid Search (Vektor + BM25 Fusion mit Recency Boost)
- CLI Interface
- Migration von memory.db
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import lancedb
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


class BrainEngine:
    """Semantic Memory System - Das neue Gedächtnis von Javix"""
    
    def __init__(self, 
                 db_path: str = None,
                 model_name: str = "nomic-ai/nomic-embed-text-v1.5",
                 vector_weight: float = 0.6,
                 bm25_weight: float = 0.4,
                 recency_boost: float = 0.1):
        """
        Initialisiere Brain Engine
        
        Args:
            db_path: Pfad zur LanceDB Datenbank
            model_name: HuggingFace Modell für Embeddings
            vector_weight: Gewichtung Vektor-Score (0-1)
            bm25_weight: Gewichtung BM25-Score (0-1)
            recency_boost: Boost-Faktor für neuere Einträge (0-1)
        """
        # Paths
        if db_path is None:
            workspace = Path(__file__).parent.parent
            db_path = workspace / "data" / "brain.lance"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Fusion-Parameter
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.recency_boost = recency_boost
        
        # Embedding Model laden
        print(f"[BRAIN] Lade Embedding-Modell: {model_name}")
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"[OK] Modell geladen (Dimension: {self.embedding_dim})")
        
        # LanceDB Connection
        self.db = lancedb.connect(str(self.db_path.parent))
        
        # Tabelle initialisieren oder laden
        self._init_table()
        
        # BM25 Index aufbauen
        self._build_bm25_index()
        
    def _init_table(self):
        """Initialisiere oder lade LanceDB Tabelle"""
        table_name = "memories"
        
        try:
            # Versuche existierende Tabelle zu laden
            self.table = self.db.open_table(table_name)
            count = len(self.table)
            print(f"[LOAD] Tabelle '{table_name}' geladen ({count} Einträge)")
        except Exception:
            # Erstelle neue Tabelle
            print(f"[NEW] Erstelle neue Tabelle '{table_name}'")
            
            # Dummy-Eintrag um Schema zu definieren
            dummy_data = [{
                "id": "init",
                "text": "Initialisierung",
                "embedding": np.zeros(self.embedding_dim).tolist(),
                "category": "system",
                "project": "",
                "importance": 1,
                "timestamp": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }]
            
            self.table = self.db.create_table(table_name, data=dummy_data)
            # Dummy-Eintrag sofort wieder löschen
            self.table.delete("id = 'init'")
            print("[OK] Tabelle erstellt")
    
    def _build_bm25_index(self):
        """BM25 Index aus allen gespeicherten Texten aufbauen"""
        print("[BM25] Baue Index...")
        
        # Alle Texte aus DB laden
        try:
            df = self.table.to_pandas()
            if len(df) == 0:
                self.bm25_corpus = []
                self.bm25_ids = []
                self.bm25 = None
                print("[WARN] Keine Einträge für BM25-Index")
                return
            
            self.bm25_corpus = df['text'].tolist()
            self.bm25_ids = df['id'].tolist()
            
            # Tokenisiere für BM25 (einfaches Whitespace-Tokenizing)
            tokenized_corpus = [text.lower().split() for text in self.bm25_corpus]
            
            # BM25 Index erstellen
            self.bm25 = BM25Okapi(tokenized_corpus)
            print(f"[OK] BM25-Index gebaut ({len(self.bm25_corpus)} Dokumente)")
            
        except Exception as e:
            print(f"[ERROR] BM25-Index Fehler: {e}")
            self.bm25 = None
            self.bm25_corpus = []
            self.bm25_ids = []
    
    def embed(self, text: str) -> List[float]:
        """
        Text zu Vektor embedden
        
        Args:
            text: Input-Text
            
        Returns:
            Embedding als Liste von Floats
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-Embedding für mehrere Texte
        
        Args:
            texts: Liste von Input-Texten
            
        Returns:
            Liste von Embeddings
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        return embeddings.tolist()
    
    def store(self, 
              text: str, 
              metadata: Optional[Dict] = None,
              entry_id: Optional[str] = None) -> str:
        """
        Text embedden und in LanceDB speichern
        
        Args:
            text: Zu speichernder Text
            metadata: Optional - category, project, importance, timestamp
            entry_id: Optional - eindeutige ID (sonst auto-generiert)
            
        Returns:
            ID des gespeicherten Eintrags
        """
        # Embedding erstellen
        embedding = self.embed(text)
        
        # Metadata defaults
        if metadata is None:
            metadata = {}
        
        # ID generieren wenn nicht gegeben
        if entry_id is None:
            entry_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Eintrag erstellen
        entry = {
            "id": entry_id,
            "text": text,
            "embedding": embedding,
            "category": metadata.get("category", "fact"),
            "project": metadata.get("project", ""),
            "importance": metadata.get("importance", 5),
            "timestamp": metadata.get("timestamp", datetime.now().isoformat()),
            "created_at": datetime.now().isoformat()
        }
        
        # In LanceDB speichern
        self.table.add([entry])
        
        # BM25 Index neu aufbauen (ineffizient, aber funktioniert)
        self._build_bm25_index()
        
        return entry_id
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Alias für search_hybrid (Standard-Suche)
        """
        return self.search_hybrid(query, top_k)
    
    def search_vector(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Reine Vektor-Suche (Cosine Similarity)
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
            
        Returns:
            Liste von Ergebnissen mit Score
        """
        # Query embedden
        query_embedding = self.embed(query)
        
        # Vektor-Suche in LanceDB
        results = self.table.search(query_embedding).limit(top_k).to_pandas()
        
        # Ergebnisse formatieren
        output = []
        for _, row in results.iterrows():
            output.append({
                "id": row['id'],
                "text": row['text'],
                "category": row['category'],
                "project": row['project'],
                "importance": row['importance'],
                "timestamp": row['timestamp'],
                "score": float(row['_distance']),  # Cosine distance (lower = better)
                "score_type": "vector"
            })
        
        return output
    
    def search_bm25(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Reine BM25-Suche (Keyword-basiert)
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
            
        Returns:
            Liste von Ergebnissen mit Score
        """
        if self.bm25 is None or len(self.bm25_corpus) == 0:
            return []
        
        # Query tokenisieren
        tokenized_query = query.lower().split()
        
        # BM25-Scores berechnen
        scores = self.bm25.get_scores(tokenized_query)
        
        # Top-K Indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        # Ergebnisse aus DB laden
        output = []
        df = self.table.to_pandas()
        
        for idx in top_indices:
            if scores[idx] == 0:
                continue  # Keine Matches
            
            entry_id = self.bm25_ids[idx]
            row = df[df['id'] == entry_id].iloc[0]
            
            output.append({
                "id": row['id'],
                "text": row['text'],
                "category": row['category'],
                "project": row['project'],
                "importance": row['importance'],
                "timestamp": row['timestamp'],
                "score": float(scores[idx]),
                "score_type": "bm25"
            })
        
        return output
    
    def search_hybrid(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Hybrid Search: Vektor + BM25 Fusion mit Recency Boost
        
        Fusion-Formel:
        final_score = (vector_score * vector_weight) + (bm25_score * bm25_weight) + recency_boost
        
        Args:
            query: Suchanfrage
            top_k: Anzahl Ergebnisse
            
        Returns:
            Liste von Ergebnissen mit fusioniertem Score
        """
        # Beide Suchen durchführen (mit höherem K für besseres Merging)
        search_k = top_k * 3
        vector_results = self.search_vector(query, search_k)
        bm25_results = self.search_bm25(query, search_k)
        
        # Scores normalisieren (0-1 Range)
        def normalize_scores(results, score_key='score'):
            if not results:
                return results
            scores = [r[score_key] for r in results]
            min_score = min(scores)
            max_score = max(scores)
            score_range = max_score - min_score if max_score != min_score else 1
            
            for r in results:
                # Vector distance -> Similarity (invertieren)
                if r.get('score_type') == 'vector':
                    r['normalized_score'] = 1 - ((r[score_key] - min_score) / score_range)
                else:
                    r['normalized_score'] = (r[score_key] - min_score) / score_range
            
            return results
        
        vector_results = normalize_scores(vector_results)
        bm25_results = normalize_scores(bm25_results)
        
        # Ergebnisse mergen
        merged = {}
        
        # Vector-Scores hinzufügen
        for r in vector_results:
            merged[r['id']] = {
                **r,
                'vector_score': r['normalized_score'],
                'bm25_score': 0.0
            }
        
        # BM25-Scores hinzufügen
        for r in bm25_results:
            if r['id'] in merged:
                merged[r['id']]['bm25_score'] = r['normalized_score']
            else:
                merged[r['id']] = {
                    **r,
                    'vector_score': 0.0,
                    'bm25_score': r['normalized_score']
                }
        
        # Recency Boost berechnen
        now = datetime.now()
        for entry in merged.values():
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                days_ago = (now - timestamp).days
                # Exponentieller Decay: neuere Einträge bekommen Boost
                entry['recency_score'] = self.recency_boost * np.exp(-days_ago / 30)
            except Exception:
                entry['recency_score'] = 0.0
        
        # Final Score berechnen
        for entry in merged.values():
            entry['final_score'] = (
                entry['vector_score'] * self.vector_weight +
                entry['bm25_score'] * self.bm25_weight +
                entry['recency_score']
            )
        
        # Nach Final Score sortieren
        sorted_results = sorted(merged.values(), key=lambda x: x['final_score'], reverse=True)
        
        # Top-K zurückgeben
        return sorted_results[:top_k]
    
    def search_with_budget(self, query: str, max_tokens: int = 1000, top_k: int = 10) -> List[Dict]:
        """
        Semantic Search mit Token-Budget.
        Returned Memories bis das Budget aufgebraucht ist.

        Args:
            query: Suchanfrage
            max_tokens: Maximale geschaetzte Tokens fuer den gesamten Context
            top_k: Maximale Ergebnisse vor Budget-Filter

        Returns:
            Liste von Memories (gefiltert nach Token-Budget)
        """
        results = self.search(query, top_k=top_k)

        selected = []
        token_count = 0

        for result in results:
            text = result.get('text', '')
            # Grobe Token-Schaetzung: 4 chars ~ 1 token
            estimated_tokens = len(text) // 4

            if token_count + estimated_tokens > max_tokens:
                break

            # Truncate auf 150 chars pro Memory
            if len(text) > 150:
                result['text'] = text[:150] + '...'
                estimated_tokens = 150 // 4

            selected.append(result)
            token_count += estimated_tokens

        return selected

    def stats(self) -> Dict:
        """
        Statistiken über die gespeicherten Memories

        Returns:
            Dict mit Statistiken
        """
        df = self.table.to_pandas()
        
        if len(df) == 0:
            return {
                "total": 0,
                "categories": {},
                "projects": {},
                "importance_avg": 0
            }
        
        # Kategorien zählen
        categories = df['category'].value_counts().to_dict()
        
        # Projekte zählen
        projects = df[df['project'] != '']['project'].value_counts().to_dict()
        
        # Durchschnittliche Importance
        importance_avg = float(df['importance'].mean())
        
        return {
            "total": len(df),
            "categories": categories,
            "projects": projects,
            "importance_avg": importance_avg
        }
    
    def migrate_from_memory_db(self, memory_db_path: str) -> int:
        """
        Migriere Einträge aus der alten memory.db SQLite-Datenbank
        
        Args:
            memory_db_path: Pfad zur memory.db
            
        Returns:
            Anzahl migrierter Einträge
        """
        print(f"\n[MIGRATE] Starte Migration von: {memory_db_path}")
        
        # SQLite DB öffnen
        conn = sqlite3.connect(memory_db_path)
        cursor = conn.cursor()
        
        # Einträge aus 'memories' Tabelle laden
        cursor.execute("""
            SELECT id, title, content, category, importance, project, created_at
            FROM memories
            WHERE active = 1
        """)
        
        rows = cursor.fetchall()
        print(f"[INFO] Gefunden: {len(rows)} aktive Einträge")
        
        if len(rows) == 0:
            conn.close()
            return 0
        
        # Batch-Embedding vorbereiten
        texts = []
        entries = []
        
        for row in rows:
            entry_id, title, content, category, importance, project, created_at = row
            
            # Text = Title + Content
            text = f"{title}\n{content}"
            texts.append(text)
            
            entries.append({
                "id": f"migrated_{entry_id}",
                "text": text,
                "category": category or "fact",
                "project": project or "",
                "importance": importance or 5,
                "timestamp": created_at,
                "created_at": datetime.now().isoformat()
            })
        
        # Batch-Embeddings erstellen
        print("[EMBED] Embeddings erstellen...")
        embeddings = self.embed_batch(texts)
        
        # Embeddings zu Einträgen hinzufügen
        for i, entry in enumerate(entries):
            entry['embedding'] = embeddings[i]
        
        # In LanceDB speichern
        print("[SAVE] Speichere in LanceDB...")
        self.table.add(entries)
        
        # BM25 Index neu aufbauen
        self._build_bm25_index()
        
        conn.close()
        print(f"[OK] Migration abgeschlossen: {len(entries)} Einträge")
        
        return len(entries)


def main():
    """CLI Interface für Brain Engine"""
    parser = argparse.ArgumentParser(description="Brain Engine - Semantic Memory System")
    subparsers = parser.add_subparsers(dest='command', help='Kommandos')
    
    # Store Kommando
    store_parser = subparsers.add_parser('store', help='Text speichern')
    store_parser.add_argument('text', type=str, help='Zu speichernder Text')
    store_parser.add_argument('--category', type=str, default='fact', help='Kategorie')
    store_parser.add_argument('--project', type=str, default='', help='Projekt')
    store_parser.add_argument('--importance', type=int, default=5, help='Wichtigkeit (1-10)')
    
    # Search Kommando
    search_parser = subparsers.add_parser('search', help='Suche durchführen')
    search_parser.add_argument('query', type=str, help='Suchanfrage')
    search_parser.add_argument('--top_k', type=int, default=5, help='Anzahl Ergebnisse')
    search_parser.add_argument('--mode', type=str, default='hybrid', 
                               choices=['hybrid', 'vector', 'bm25'],
                               help='Such-Modus')
    
    # Stats Kommando
    stats_parser = subparsers.add_parser('stats', help='Statistiken anzeigen')
    
    # Migrate Kommando
    migrate_parser = subparsers.add_parser('migrate', help='memory.db migrieren')
    migrate_parser.add_argument('--db', type=str, 
                                default=r'C:\Users\jarvi\.openclaw\workspace\memory.db',
                                help='Pfad zur memory.db')
    
    args = parser.parse_args()
    
    # Brain Engine initialisieren
    try:
        brain = BrainEngine()
    except Exception as e:
        print(f"[ERROR] Fehler beim Initialisieren: {e}")
        sys.exit(1)
    
    # Kommandos ausführen
    if args.command == 'store':
        metadata = {
            "category": args.category,
            "project": args.project,
            "importance": args.importance
        }
        entry_id = brain.store(args.text, metadata)
        print(f"[OK] Gespeichert: {entry_id}")
    
    elif args.command == 'search':
        # Suchmodus wählen
        if args.mode == 'vector':
            results = brain.search_vector(args.query, args.top_k)
        elif args.mode == 'bm25':
            results = brain.search_bm25(args.query, args.top_k)
        else:  # hybrid
            results = brain.search_hybrid(args.query, args.top_k)
        
        # Ergebnisse ausgeben
        print(f"\n[SEARCH] Suche: '{args.query}' (Modus: {args.mode})")
        print(f"[INFO] {len(results)} Ergebnisse:\n")
        
        for i, r in enumerate(results, 1):
            print(f"{'='*80}")
            print(f"#{i} | Score: {r.get('final_score', r.get('score', 0)):.4f}")
            print(f"Kategorie: {r['category']} | Projekt: {r['project']} | Wichtigkeit: {r['importance']}")
            print(f"Timestamp: {r['timestamp']}")
            if args.mode == 'hybrid':
                print(f"Scores: Vector={r.get('vector_score', 0):.3f} | BM25={r.get('bm25_score', 0):.3f} | Recency={r.get('recency_score', 0):.3f}")
            print(f"\nText:\n{r['text'][:500]}...")
            print()
    
    elif args.command == 'stats':
        stats = brain.stats()
        print("\n[STATS] Brain Engine Statistiken")
        print(f"{'='*80}")
        print(f"Gesamt: {stats['total']} Einträge")
        print(f"Durchschnittliche Wichtigkeit: {stats['importance_avg']:.2f}")
        print(f"\nKategorien:")
        for cat, count in stats['categories'].items():
            print(f"  - {cat}: {count}")
        print(f"\nProjekte:")
        for proj, count in stats['projects'].items():
            print(f"  - {proj}: {count}")
    
    elif args.command == 'migrate':
        if not os.path.exists(args.db):
            print(f"[ERROR] memory.db nicht gefunden: {args.db}")
            sys.exit(1)
        
        count = brain.migrate_from_memory_db(args.db)
        print(f"\n[OK] Migration erfolgreich: {count} Einträge")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
