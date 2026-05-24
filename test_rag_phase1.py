"""
VERA Office - RAG Phase 1 Test
Indexierung + 5 Test-Queries
"""

import sys
import time
from pathlib import Path

# Backend Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.core.rag_engine import RAGEngine

def test_rag_phase1():
    """
    Test RAG Phase 1:
    1. Initialize Engine
    2. Index Documents
    3. Run 5 Test Queries
    """
    
    print("=" * 80)
    print("VERA Office - RAG Phase 1 Test")
    print("=" * 80)
    print()
    
    # 1. Initialize
    print("📦 Initialisiere RAG Engine...")
    start = time.time()
    
    rag = RAGEngine(
        db_path="data/vera.db",
        chroma_path="data/chroma",
        model_name="intfloat/multilingual-e5-large"
    )
    
    init_time = time.time() - start
    print(f"✅ Engine geladen in {init_time:.1f}s")
    print()
    
    # 2. Stats vor Indexierung
    print("📊 Stats vor Indexierung:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 3. Index Documents (force=True wenn bereits indexiert)
    print("🔄 Indexiere Dokumente...")
    index_start = time.time()
    
    # Check if already indexed
    if stats["indexed_documents"] > 0:
        print(f"⚠️  Collection bereits indexiert ({stats['indexed_documents']} Docs)")
        print("   Überspringe Indexierung (nutze force=True für Re-Index)")
        report = {
            "status": "skipped",
            "indexed_count": stats["indexed_documents"]
        }
    else:
        report = rag.index_documents(force=False)
        index_time = time.time() - index_start
        print(f"✅ Indexierung abgeschlossen in {index_time:.1f}s")
        print(f"   Indexed: {report['indexed_count']}")
        print(f"   Failed: {report['failed_count']}")
        print(f"   Total: {report['total_documents']}")
    
    print()
    
    # 4. Stats nach Indexierung
    print("📊 Stats nach Indexierung:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # 5. Test Queries
    print("🔍 Test Queries:")
    print("=" * 80)
    
    test_queries = [
        "Hygieneplan Desinfektion",
        "Notfall Reanimation",
        "Datenschutz Patientenakte",
        "Prüfprotokoll Sterilisation",
        "Arbeitsanweisung Behandlung"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print()
        print(f"{i}. Query: '{query}'")
        print("-" * 80)
        
        query_start = time.time()
        results = rag.search(query, top_k=3)
        query_time = time.time() - query_start
        
        print(f"   Zeit: {query_time:.3f}s | Ergebnisse: {len(results)}")
        print()
        
        if results:
            for j, result in enumerate(results, 1):
                print(f"   {j}. {result['filename']}")
                print(f"      Relevance: {result['relevance_score']:.3f} | Category: {result['category']}")
                print(f"      Preview: {result['preview'][:100]}...")
                print()
        else:
            print("   ❌ Keine Ergebnisse gefunden")
            print()
    
    print("=" * 80)
    print("✅ RAG Phase 1 Test abgeschlossen!")
    print("=" * 80)


if __name__ == "__main__":
    test_rag_phase1()
