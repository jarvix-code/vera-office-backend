"""
VERA Office - RAG Engine (Phase 1)
Embedding + Vector Search für QM-Dokumente
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Retrieval-Augmented Generation Engine für VERA Office
    
    Features:
    - Embedding Model: intfloat/multilingual-e5-large (1024 dims)
    - Vector Store: ChromaDB (persistent)
    - Query: Semantic search über QM-Dokumente
    """
    
    def __init__(
        self, 
        db_path: str = "data/vera.db",
        chroma_path: str = "data/chroma",
        model_name: str = "intfloat/multilingual-e5-large"
    ):
        self.db_path = Path(db_path)
        self.chroma_path = Path(chroma_path)
        self.model_name = model_name
        
        # Embedding Model laden
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # ChromaDB initialisieren
        logger.info(f"Initializing ChromaDB at: {chroma_path}")
        self.chroma = chromadb.PersistentClient(path=str(self.chroma_path))
        
        # Collection laden oder erstellen
        try:
            self.collection = self.chroma.get_collection("qm-documents")
            logger.info("Loaded existing collection 'qm-documents'")
        except:
            self.collection = self.chroma.create_collection("qm-documents")
            logger.info("Created new collection 'qm-documents'")
    
    def index_documents(self, force: bool = False) -> Dict[str, Any]:
        """
        Alle QM-Dokumente aus der DB einlesen und embedden
        
        Args:
            force: Wenn True, überschreibt bestehende Embeddings
        
        Returns:
            Report mit Statistiken
        """
        # Check ob bereits indexiert
        existing_count = self.collection.count()
        if existing_count > 0 and not force:
            logger.info(f"Collection already has {existing_count} documents. Use force=True to re-index.")
            return {
                "status": "skipped",
                "existing_count": existing_count,
                "message": "Collection already indexed. Use force=True to re-index."
            }
        
        # Bei force: Collection leeren
        if force and existing_count > 0:
            logger.info("Force re-index: deleting existing collection")
            self.chroma.delete_collection("qm-documents")
            self.collection = self.chroma.create_collection("qm-documents")
        
        # Dokumente aus DB laden
        logger.info("Loading documents from database...")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT d.id, d.filename, d.ocr_text, 
                   COALESCE(c.name, 'Uncategorized') as category
            FROM documents d
            LEFT JOIN categories c ON d.category_id = c.id
            WHERE d.ocr_text IS NOT NULL 
            AND length(d.ocr_text) > 100
            ORDER BY d.id
        """)
        docs = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(docs)} documents to index")
        
        # Embeddings erstellen (batch processing)
        indexed_count = 0
        failed_count = 0
        
        for doc_id, filename, text, category in docs:
            try:
                # Embedding erstellen
                embedding = self.model.encode(text, show_progress_bar=False)
                
                # In ChromaDB speichern
                self.collection.add(
                    ids=[str(doc_id)],
                    embeddings=[embedding.tolist()],
                    metadatas=[{
                        'filename': filename or '',
                        'category': category or 'Uncategorized',
                        'doc_id': doc_id
                    }],
                    documents=[text[:1000]]  # Preview (erste 1000 Zeichen)
                )
                
                indexed_count += 1
                
                if indexed_count % 50 == 0:
                    logger.info(f"Indexed {indexed_count}/{len(docs)} documents...")
                
            except Exception as e:
                logger.error(f"Failed to index document {doc_id}: {e}")
                failed_count += 1
        
        logger.info(f"Indexing complete: {indexed_count} success, {failed_count} failed")
        
        return {
            "status": "success",
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "total_documents": len(docs),
            "collection_count": self.collection.count()
        }
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic Search über QM-Dokumente
        
        Args:
            query: Suchanfrage (natural language)
            top_k: Anzahl der Top-Ergebnisse
            category_filter: Optional - nur Dokumente dieser Kategorie
        
        Returns:
            Liste von Results mit metadata, document, distance
        """
        # Query Embedding erstellen
        query_embedding = self.model.encode(query, show_progress_bar=False)
        
        # Where-Filter für Kategorie
        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where_filter
        )
        
        # Results formatieren
        formatted_results = []
        
        if results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'doc_id': results['metadatas'][0][i].get('doc_id'),
                    'filename': results['metadatas'][0][i].get('filename', ''),
                    'category': results['metadatas'][0][i].get('category', 'Uncategorized'),
                    'preview': results['documents'][0][i] if results['documents'] else '',
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'relevance_score': 1 - (results['distances'][0][i] if results['distances'] else 0)
                })
        
        return formatted_results
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Vollständiges Dokument aus der DB laden
        
        Args:
            doc_id: Dokument-ID
        
        Returns:
            Dokument-Dict oder None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT d.id, d.filename, d.ocr_text, 
                   COALESCE(c.name, 'Uncategorized') as category,
                   d.created_at, d.file_path
            FROM documents d
            LEFT JOIN categories c ON d.category_id = c.id
            WHERE d.id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'filename': row[1],
                'ocr_text': row[2],
                'category': row[3],
                'created_at': row[4],
                'file_path': row[5]
            }
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Statistiken über die RAG-Engine
        """
        collection_count = self.collection.count()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT COUNT(*) 
            FROM documents 
            WHERE ocr_text IS NOT NULL 
            AND length(ocr_text) > 100
        """)
        db_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "model": self.model_name,
            "vector_store": "ChromaDB",
            "indexed_documents": collection_count,
            "available_documents": db_count,
            "index_coverage": f"{(collection_count/db_count*100):.1f}%" if db_count > 0 else "0%",
            "embedding_dimension": 1024,
            "chroma_path": str(self.chroma_path),
            "db_path": str(self.db_path)
        }


# Singleton Instance (lazy loading)
_rag_engine: Optional[RAGEngine] = None

def get_rag_engine() -> RAGEngine:
    """
    Singleton Factory für RAG Engine
    """
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
