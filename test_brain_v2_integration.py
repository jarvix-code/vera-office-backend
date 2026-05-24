"""
Test Brain v2 Integration in VERA
"""
import sys
sys.path.insert(0, '.')

from backend.core.ai.brain import brain

print("🧠 TESTING VERA BRAIN V2 INTEGRATION\n")

# Test 1: Store with embeddings
print("1️⃣ Storing semantic learning...")
log_id = brain.store_semantic_learning(
    event_type="test",
    description="Brain v2 semantic search integration test",
    data='{"status": "testing", "features": ["hybrid_search", "knowledge_graph"]}'
)
print(f"   ✅ Stored log #{log_id}\n")

# Test 2: Semantic search
print("2️⃣ Testing semantic search...")
results = brain.semantic_search("brain semantic", top_k=5)
print(f"   Found {len(results)} results:\n")

for log_id, score, data in results:
    print(f"   [{score:.3f}] #{log_id} | {data['event_type']}")
    print(f"           {data['description'][:80]}")
    print()

# Test 3: Search existing VERA data
print("3️⃣ Searching existing VERA learning...")
results = brain.semantic_search("document classification", top_k=3)
print(f"   Found {len(results)} classification-related entries:\n")

for log_id, score, data in results:
    print(f"   [{score:.3f}] {data['description'][:60]}")

print("\n✅ INTEGRATION TEST COMPLETE!")
