"""Quick test for Sprint 2 components."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Jarvix\vera-office")
os.environ["PYTHONPATH"] = r"C:\Jarvix\vera-office"

print("=" * 60)
print("SPRINT 2 — Component Tests")
print("=" * 60)

# 1. Test template knowledge
print("\n1. Template Knowledge:")
from backend.core.ai.template_knowledge import get_all_categories, get_categories_prompt_text
cats = get_all_categories("arztpraxis")
print(f"   {len(cats)} categories loaded for 'arztpraxis'")
for c in cats[:5]:
    print(f"   - {c['name']}: {c['description']}")

# 2. Test llama-cpp-python
print("\n2. llama-cpp-python:")
try:
    from llama_cpp import Llama
    print("   ✅ llama-cpp-python imported successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")

# 3. Test model file existence
print("\n3. Model files:")
from pathlib import Path
models_dir = Path(r"C:\Jarvix\vera-office\models")
for f in models_dir.glob("*.gguf"):
    size_mb = f.stat().st_size / (1024*1024)
    print(f"   ✅ {f.name} ({size_mb:.0f} MB)")

# 4. Test LLM Manager (without loading model to save time)
print("\n4. LLM Manager config:")
from backend.core.ai.llm_manager import LLMManager
mgr = LLMManager()
print(f"   Model path: {mgr._config.get('model_path')}")
print(f"   n_threads: {mgr._config.get('n_threads')}")
print(f"   Available: {mgr.is_available()}")

# 5. Test classifier (keyword fallback)
print("\n5. Classifier (keyword fallback):")
from backend.core.ai.classifier import classifier
result = classifier._keyword_fallback(
    "Rechnung Nr. 12345 vom 15.02.2026 Netto: 500.00 EUR MwSt: 95.00 EUR Brutto: 595.00 EUR"
)
print(f"   Category: {result['category']}")
print(f"   Confidence: {result['confidence']}")
print(f"   Reasoning: {result['reasoning']}")

# 6. Test vision checker module
print("\n6. Vision Checker:")
from backend.core.ai.vision_checker import vision_checker
print(f"   Module loaded OK")

# 7. Test feedback store
print("\n7. Feedback Store:")
from backend.core.ai.feedback_store import feedback_store
print(f"   Total feedback: {feedback_store.get_total_feedback_count()}")

# 8. Test namer
print("\n8. Document Namer:")
from backend.core.ai.namer import namer
fallback = namer._fallback_filename("rechnung_eingang", "test_invoice.pdf")
print(f"   Fallback name: {fallback}")

print("\n" + "=" * 60)
print("All component tests completed!")
print("=" * 60)
