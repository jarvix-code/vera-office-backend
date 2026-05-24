#!/usr/bin/env python3
"""
VERA Verification System - Runner Script
Führt alle Verifikations-Checks aus und generiert Report.

Usage:
    python run_verification.py [--full] [--report report.html]
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json


def print_banner():
    """Print fancy banner"""
    print("\n" + "="*70)
    print("  VERA VERIFICATION SYSTEM")
    print("  Test-First Development für Production Readiness")
    print("="*70 + "\n")


def check_dependencies():
    """Check if pytest is installed"""
    print("[1/5] Checking dependencies...")
    try:
        import pytest
        print(f"  ✓ pytest installed (version {pytest.__version__})")
        return True
    except ImportError:
        print("  ✗ pytest not installed!")
        print("  Install with: pip install pytest pytest-cov")
        return False


def run_tests(full=False):
    """Run test suite"""
    print("\n[2/5] Running tests...")
    
    # Test command
    cmd = ["pytest", "tests/", "-v"]
    
    if not full:
        # Quick tests only (exclude slow tests)
        cmd.extend(["-m", "not slow"])
        print("  Running quick tests only (use --full for complete suite)")
    else:
        print("  Running complete test suite (including slow tests)")
    
    # Add coverage
    cmd.extend(["--cov=backend.core.ai", "--cov-report=term-missing"])
    
    # Run
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    return result.returncode == 0


def check_rag_index():
    """Check if RAG index is populated"""
    print("\n[3/5] Checking RAG index...")
    try:
        from backend.core.rag_engine import RAGEngine
        rag = RAGEngine()
        count = rag.collection.count()
        
        if count > 0:
            print(f"  ✓ RAG index has {count} documents")
            return True
        else:
            print(f"  ✗ RAG index is EMPTY!")
            print(f"  Action: Index documents first")
            return False
    
    except Exception as e:
        print(f"  ✗ RAG check failed: {e}")
        return False


def check_classifier():
    """Check if classifier is available"""
    print("\n[4/5] Checking classifier...")
    try:
        from backend.core.ai.safe_classifier import safe_classifier
        stats = safe_classifier.get_stats()
        
        print(f"  Confidence Threshold: {stats['min_confidence']:.0%}")
        print(f"  RAG Enabled: {stats['rag_enabled']}")
        print(f"  Classifier Available: {stats['classifier_available']}")
        
        if stats['classifier_available']:
            print(f"  ✓ Classifier ready")
            return True
        else:
            print(f"  ✗ Classifier NOT available!")
            print(f"  Action: Check LLM model")
            return False
    
    except Exception as e:
        print(f"  ✗ Classifier check failed: {e}")
        return False


def check_ground_truth():
    """Check ground truth dataset"""
    print("\n[5/5] Checking ground truth dataset...")
    try:
        gt_file = Path("tests/fixtures/ground_truth.json")
        
        if not gt_file.exists():
            print(f"  ✗ Ground truth file not found!")
            return False
        
        with open(gt_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        samples = data.get("samples", [])
        total = len(samples)
        distribution = data.get("metadata", {}).get("distribution", {})
        
        print(f"  Total Samples: {total}")
        print(f"  Distribution:")
        for cat, count in distribution.items():
            print(f"    - {cat}: {count}")
        
        if total >= 30:
            print(f"  ✓ Ground truth dataset OK ({total} samples)")
            return True
        else:
            print(f"  ⚠ Only {total} samples (target: 50+)")
            return True  # Not critical
    
    except Exception as e:
        print(f"  ✗ Ground truth check failed: {e}")
        return False


def generate_report():
    """Generate verification report"""
    print("\n" + "="*70)
    print("  VERIFICATION REPORT")
    print("="*70)
    
    # Summary
    checks = {
        "Dependencies": check_dependencies(),
        "Ground Truth": check_ground_truth(),
        "RAG Index": check_rag_index(),
        "Classifier": check_classifier(),
    }
    
    passed = sum(checks.values())
    total = len(checks)
    
    print(f"\nPassed: {passed}/{total}")
    
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
    
    # Recommendation
    print("\n" + "-"*70)
    if passed == total:
        print("✅ ALL CHECKS PASSED - Ready for testing!")
        print("\nNext Steps:")
        print("  1. Run: python run_verification.py --full")
        print("  2. Check test results")
        print("  3. If accuracy >= 85%: Start Demo-Phase")
    else:
        print("❌ SOME CHECKS FAILED - Fix issues first!")
        print("\nActions Required:")
        for check, result in checks.items():
            if not result:
                print(f"  - Fix: {check}")
        print("\nSee VERIFICATION_CHECKLIST.md for details")
    
    print("="*70 + "\n")
    
    return passed == total


def main():
    """Main verification workflow"""
    # Parse args
    full = "--full" in sys.argv
    
    print_banner()
    
    # Run checks
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n❌ Dependencies missing - install first!")
        sys.exit(1)
    
    gt_ok = check_ground_truth()
    rag_ok = check_rag_index()
    clf_ok = check_classifier()
    
    # Run tests if checks passed
    if deps_ok and gt_ok:
        tests_ok = run_tests(full=full)
    else:
        print("\n⚠ Skipping tests due to failed checks")
        tests_ok = False
    
    # Generate report
    print("\n")
    all_ok = generate_report()
    
    # Exit code
    sys.exit(0 if all_ok and tests_ok else 1)


if __name__ == "__main__":
    main()
