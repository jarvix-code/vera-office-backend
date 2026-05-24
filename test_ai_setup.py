"""
VERA Office - AI Setup Test Script
Prueft ob alle AI-Dependencies korrekt installiert sind.
KEINE EMOJIS (Windows cp1252 Problem)
"""

import sys
from pathlib import Path

print("=" * 60)
print("VERA Office - AI Setup Check")
print("=" * 60)

# Test 1: Imports
print("\n1. Testing imports...")
try:
    from backend.core.ai import llm, classifier, namer, filer, feedback_store
    print("   [OK] All AI modules imported successfully")
except ImportError as e:
    print(f"   [ERR] Import failed: {e}")
    sys.exit(1)

# Test 2: LLM Availability
print("\n2. Testing LLM availability...")
available = llm.is_available()
if available:
    print("   [OK] LLM available (llama-cpp-python + model loaded)")
else:
    print("   [WARN] LLM not available (this is OK for testing)")
    print("          -> To enable: Install llama-cpp-python + download model")
    print("          -> See AI_SETUP.md for instructions")

# Test 3: Dependencies
print("\n3. Checking dependencies...")
deps = {
    'scikit-learn': 'sklearn',
    'zeroconf': 'zeroconf',
    'fastapi': 'fastapi',
    'sqlalchemy': 'sqlalchemy'
}

missing = []
for name, module in deps.items():
    try:
        __import__(module)
        print(f"   [OK] {name}")
    except ImportError:
        print(f"   [ERR] {name} missing")
        missing.append(name)

if missing:
    print(f"\n   [WARN] Missing dependencies: {', '.join(missing)}")
    print("          -> Run: pip install -r requirements.txt")

# Test 4: Model file
print("\n4. Checking model file...")
model_path = Path(__file__).parent / "models" / "mistral-7b-instruct-v0.3.Q4_K_M.gguf"
if model_path.exists():
    size_gb = model_path.stat().st_size / (1024**3)
    print(f"   [OK] Model found: {model_path.name} ({size_gb:.2f} GB)")
else:
    print(f"   [WARN] Model not found: {model_path}")
    print("          -> Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF")
    print(f"          -> Save to: {model_path}")

# Test 5: Config
print("\n5. Checking configuration...")
config_path = Path(__file__).parent / "config" / "vera.yaml"
if config_path.exists():
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'ai' in config:
        print("   [OK] AI config found in vera.yaml")
        print(f"        - confidence_threshold: {config['ai'].get('confidence_threshold')}")
        print(f"        - auto_confirm_threshold: {config['ai'].get('auto_confirm_threshold')}")
    else:
        print("   [ERR] AI config missing in vera.yaml")
else:
    print(f"   [ERR] Config file not found: {config_path}")

# Test 6: Feedback Store
print("\n6. Testing Feedback Store...")
try:
    total = feedback_store.get_total_feedback_count()
    print(f"   [OK] Feedback Store initialized (entries: {total})")
except Exception as e:
    print(f"   [ERR] Feedback Store error: {e}")

# Summary
print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)

if available:
    print("[OK] FULLY READY - All AI features available")
else:
    print("[WARN] PARTIALLY READY - Core features work, AI disabled")
    print("\nTo enable AI:")
    print("1. Install llama-cpp-python (see AI_SETUP.md)")
    print("2. Download model (4.4 GB)")
    print("3. Re-run this test")

print("\nNext steps:")
print("1. Start backend: python -m uvicorn backend.main:app --reload")
print("2. Check logs for 'LLM model loaded successfully'")
print("3. Test API: http://localhost:8000/api/docs")

print("=" * 60)
