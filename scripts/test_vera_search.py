"""Test VERA Brain Search"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from backend.core.vera_brain import vera_brain

# Test search
query = "Hygieneplan"
print(f"Suche: {query}\n")

results = vera_brain.search_documents(query, doc_type="qm")

print(f"Gefunden: {len(results)} Dokumente\n")

for i, doc in enumerate(results[:5], 1):
    print(f"{i}. {doc['title']}")
    print(f"   Preview: {doc['preview'][:100]}...")
    print()
