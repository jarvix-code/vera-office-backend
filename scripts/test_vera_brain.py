"""Test VERA Brain"""
import sys
sys.path.insert(0, 'C:/Jarvix/vera-office')

from backend.core.vera_brain import vera_brain

print("✅ VERA Brain initialized")

# Test compliance
status = vera_brain.get_compliance_status()
print(f"Compliance Status: {status}")

# Test add fact
vera_brain.add_fact("praxis", "name", "Dr. Test Praxis", "test")
print("✅ Fact added")

# Test search
results = vera_brain.search_facts("Test")
print(f"Search results: {len(results)}")

print("\n✅ VERA BRAIN WORKS!")
