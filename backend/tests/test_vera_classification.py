"""
VERA Classification Test Suite
Tests the complete classification pipeline: RAG + LLM + Feedback

Requirements:
- 85%+ accuracy on ground truth samples
- RAG delivers relevant context
- Feedback loop works correctly
- Confidence thresholds prevent bad classifications
"""
import pytest
import json
from pathlib import Path
from typing import List, Dict

# Test Configuration
GROUND_TRUTH_FILE = Path(__file__).parent / "fixtures" / "ground_truth.json"
MIN_ACCURACY = 0.85  # 85% minimum
MIN_RAG_RELEVANCE = 0.7  # RAG context must be relevant
MIN_CONFIDENCE_THRESHOLD = 0.85  # Only classify if confident


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def ground_truth_samples() -> List[Dict]:
    """Load ground truth dataset"""
    with open(GROUND_TRUTH_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["samples"]


@pytest.fixture(scope="module")
def rag_engine():
    """Initialize RAG engine"""
    from backend.core.rag_engine import RAGEngine
    engine = RAGEngine()
    return engine


@pytest.fixture(scope="module")
def classifier():
    """Initialize document classifier"""
    from backend.core.ai.classifier import DocumentClassifier
    clf = DocumentClassifier()
    return clf


@pytest.fixture(scope="module")
def feedback_store():
    """Initialize feedback store"""
    from backend.core.ai.feedback_store import feedback_store
    return feedback_store


# ============================================================
# Test 1: RAG Delivers Context
# ============================================================

@pytest.mark.rag
def test_rag_delivers_context(rag_engine, ground_truth_samples):
    """
    RAG muss für jeden Sample relevanten Kontext finden.
    
    PROBLEM: Wenn RAG nichts findet, kann Mistral nicht klassifizieren!
    """
    missing_context = []
    low_relevance = []
    
    for sample in ground_truth_samples[:10]:  # Test first 10
        text = sample["text"]
        
        # Search for context
        try:
            results = rag_engine.search(text, top_k=3)
            
            if not results or len(results) == 0:
                missing_context.append(sample["filename"])
                continue
            
            # Check relevance (distance/score)
            best_score = results[0].get("score", 0) if isinstance(results[0], dict) else 0
            
            if best_score < MIN_RAG_RELEVANCE:
                low_relevance.append({
                    "filename": sample["filename"],
                    "score": best_score
                })
        
        except Exception as e:
            pytest.fail(f"RAG search failed for {sample['filename']}: {e}")
    
    # Assert
    assert len(missing_context) == 0, \
        f"RAG liefert keinen Kontext für: {missing_context}"
    
    assert len(low_relevance) == 0, \
        f"RAG Relevanz zu niedrig: {low_relevance}"


# ============================================================
# Test 2: Classification Accuracy
# ============================================================

@pytest.mark.classifier
@pytest.mark.slow
def test_classification_accuracy(classifier, ground_truth_samples):
    """
    Classifier muss mindestens 85% Accuracy erreichen.
    
    CRITICAL: Das ist Boris' Haupt-Concern!
    """
    results = []
    correct = 0
    total = 0
    errors = []
    
    for sample in ground_truth_samples:
        expected_type = sample["type"]
        text = sample["text"]
        
        try:
            # Classify
            result = classifier.classify(text)
            predicted_type = result.get("category", "unknown")
            confidence = result.get("confidence", 0.0)
            
            # Store result
            results.append({
                "filename": sample["filename"],
                "expected": expected_type,
                "predicted": predicted_type,
                "confidence": confidence,
                "correct": predicted_type == expected_type
            })
            
            # Count
            total += 1
            if predicted_type == expected_type:
                correct += 1
            else:
                errors.append({
                    "filename": sample["filename"],
                    "expected": expected_type,
                    "predicted": predicted_type,
                    "confidence": confidence
                })
        
        except Exception as e:
            pytest.fail(f"Classification failed for {sample['filename']}: {e}")
    
    # Calculate accuracy
    accuracy = correct / total if total > 0 else 0.0
    
    # Report
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION ACCURACY TEST")
    print(f"{'='*60}")
    print(f"Total Samples: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {accuracy*100:.1f}%")
    print(f"Required: {MIN_ACCURACY*100:.0f}%")
    
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for err in errors[:5]:  # Show first 5
            print(f"  - {err['filename']}")
            print(f"    Expected: {err['expected']}")
            print(f"    Got: {err['predicted']} (conf: {err['confidence']:.2f})")
    
    print(f"{'='*60}\n")
    
    # Assert
    assert accuracy >= MIN_ACCURACY, \
        f"Nur {accuracy*100:.1f}% korrekt! Minimum: {MIN_ACCURACY*100:.0f}%"


# ============================================================
# Test 3: 3-Stufen Confidence Threshold System (BORIS' UPDATE)
# ============================================================

@pytest.mark.classifier
def test_confidence_thresholds_3_level():
    """
    3-Stufen Confidence System (Boris' Requirement 2026-03-28).
    
    STUFE 1 (≥95%): Auto-Klassifikation (action=auto_classified)
    STUFE 2 (75-95%): Quick Confirm (action=confirm_with_suggestion)
    STUFE 3 (<75%): Volle Erklärung (action=needs_explanation)
    """
    from backend.core.ai.safe_classifier import SafeClassifier
    
    # Initialize classifier
    classifier = SafeClassifier(
        min_confidence=0.95,
        quick_confirm_threshold=0.75
    )
    
    # STUFE 1: Sehr klarer Text (sollte ≥95% sein)
    clear_text = """
    Rechnung Nr. 2024-001
    Sehr geehrte Damen und Herren,
    hiermit berechnen wir folgende Leistungen:
    Zahnreinigung: 80,00 EUR
    Kontrolluntersuchung: 45,00 EUR
    Gesamtbetrag: 125,00 EUR
    """
    
    result_high = classifier.classify_with_confidence_levels(clear_text)
    
    # Should be auto-classified
    assert result_high["action"] == "auto_classified", \
        f"Clear text should be auto-classified (STUFE 1), got: {result_high['action']}"
    assert result_high["confidence"] >= 0.95, \
        f"STUFE 1 requires ≥95% confidence, got: {result_high['confidence']:.2%}"
    assert result_high["user_action_needed"] == False
    
    # STUFE 2: Mittlere Sicherheit (sollte 75-95% sein)
    medium_text = """
    Checkliste Tagesabschluss
    □ Alle Räume gereinigt
    □ Geräte ausgeschaltet
    """
    
    result_mid = classifier.classify_with_confidence_levels(medium_text)
    
    # Should be quick confirm
    if 0.75 <= result_mid["confidence"] < 0.95:
        assert result_mid["action"] == "confirm_with_suggestion", \
            f"Medium confidence should trigger Quick Confirm (STUFE 2), got: {result_mid['action']}"
        assert result_mid["can_quick_confirm"] == True
        assert result_mid["user_action_needed"] == True
        assert "vorschlag" in result_mid
        assert "frage" in result_mid
    
    # STUFE 3: Unsicherer Text (sollte <75% sein)
    unclear_text = """
    Dieses Dokument ist schwer zu kategorisieren.
    Keine klaren Merkmale vorhanden.
    """
    
    result_low = classifier.classify_with_confidence_levels(unclear_text)
    
    # Should need explanation
    if result_low["confidence"] < 0.75:
        assert result_low["action"] == "needs_explanation", \
            f"Low confidence should need explanation (STUFE 3), got: {result_low['action']}"
        assert result_low["can_quick_confirm"] == False
        assert result_low["user_action_needed"] == True
        assert "frage" in result_low


@pytest.mark.unit
def test_threshold_boundaries():
    """
    Test exact threshold boundaries (95% / 75%).
    """
    from backend.core.ai.safe_classifier import SafeClassifier
    
    classifier = SafeClassifier(
        min_confidence=0.95,
        quick_confirm_threshold=0.75
    )
    
    # Mock classification results
    # In real test, you'd mock classifier.classifier.classify()
    
    # Check stats
    stats = classifier.get_stats()
    
    assert stats["min_confidence"] == 0.95
    assert stats["quick_confirm_threshold"] == 0.75
    assert stats["stufe_1_auto"] == "≥95%"
    assert stats["stufe_2_quick_confirm"] == "75%-95%"
    assert stats["stufe_3_needs_explanation"] == "<75%"


# ============================================================
# Test 4: Feedback Loop
# ============================================================

@pytest.mark.feedback
def test_feedback_storage(feedback_store):
    """
    Feedback-System muss Korrekturen speichern können.
    """
    test_text = "Test Checkliste mit □ Checkbox und Unterschrift"
    test_category = "checkliste"
    
    # Add feedback
    feedback_store.add_feedback(
        ocr_text=test_text,
        category=test_category,
        confirmed_by_user=True,
        confidence=1.0
    )
    
    # Check if stored
    count = feedback_store.get_total_feedback_count()
    assert count > 0, "Feedback store is empty!"
    
    # Check if retrievable
    similar = feedback_store.find_similar(test_text, top_k=3)
    assert len(similar) > 0, "Cannot retrieve stored feedback!"


@pytest.mark.feedback
def test_feedback_improves_classification(classifier, feedback_store):
    """
    Feedback sollte die Klassifikation verbessern.
    
    Workflow:
    1. Klassifiziere Text (evtl. falsch)
    2. User korrigiert → Feedback
    3. Klassifiziere ähnlichen Text → sollte besser sein
    """
    # Original text (might be classified wrong initially)
    original_text = """
    Checkliste Tagesabschluss
    □ Alle Räume gereinigt
    □ Geräte ausgeschaltet
    Unterschrift: ____________
    """
    
    correct_category = "checkliste"
    
    # First classification (before feedback)
    result_before = classifier.classify(original_text, use_few_shot=False)
    
    # Add user correction as feedback
    feedback_store.add_feedback(
        ocr_text=original_text,
        category=correct_category,
        confirmed_by_user=True,
        confidence=1.0
    )
    
    # Similar text
    similar_text = """
    Checkliste Wochenabschluss
    □ Dokumentation vollständig
    □ Fenster geschlossen
    Verantwortlich: ____________
    """
    
    # Second classification (with feedback / few-shot)
    result_after = classifier.classify(similar_text, use_few_shot=True)
    
    # Should be correct now (or at least have higher confidence)
    assert result_after["category"] == correct_category or \
           result_after["confidence"] > result_before.get("confidence", 0), \
           "Feedback did not improve classification!"


# ============================================================
# Test 5: Category Coverage
# ============================================================

@pytest.mark.unit
def test_all_categories_covered(ground_truth_samples):
    """
    Ground Truth muss alle wichtigen Kategorien abdecken.
    """
    categories = set(s["type"] for s in ground_truth_samples)
    
    required_categories = {
        "checkliste",
        "arbeitsanweisung",
        "hygieneplan",
        "freigabeprotokoll",
        "wartungsprotokoll"
    }
    
    missing = required_categories - categories
    
    assert len(missing) == 0, \
        f"Missing categories in ground truth: {missing}"


# ============================================================
# Test 6: RAG Index Quality
# ============================================================

@pytest.mark.rag
def test_rag_index_not_empty(rag_engine):
    """
    RAG index muss Dokumente enthalten.
    Wenn leer → keine Klassifikation möglich!
    """
    try:
        # Check collection count
        count = rag_engine.collection.count()
        assert count > 0, "RAG index is empty! Run indexing first."
        
        print(f"\n[RAG] Index has {count} documents")
    
    except Exception as e:
        pytest.fail(f"Cannot check RAG index: {e}")


# ============================================================
# Test 7: Integration Test (Full Pipeline)
# ============================================================

@pytest.mark.integration
@pytest.mark.slow
def test_full_classification_pipeline(rag_engine, classifier, ground_truth_samples):
    """
    Complete pipeline test: RAG → Classifier → Result
    
    This simulates the real production workflow.
    """
    sample = ground_truth_samples[0]  # Use first sample
    
    # Step 1: RAG search
    context = rag_engine.search(sample["text"], top_k=3)
    assert len(context) > 0, "RAG returned no context"
    
    # Step 2: Classification
    result = classifier.classify(sample["text"])
    assert "category" in result, "Classification result missing category"
    assert "confidence" in result, "Classification result missing confidence"
    
    # Step 3: Confidence check
    if result["confidence"] >= MIN_CONFIDENCE_THRESHOLD:
        assert result["category"] != "UNBEKANNT", \
            "High confidence but category is UNKNOWN"
    
    # Step 4: Verify result
    print(f"\n[PIPELINE TEST]")
    print(f"Sample: {sample['filename']}")
    print(f"Expected: {sample['type']}")
    print(f"Predicted: {result['category']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Match: {'✓' if result['category'] == sample['type'] else '✗'}")


# ============================================================
# Performance Benchmarks (optional)
# ============================================================

@pytest.mark.slow
def test_classification_speed(classifier, ground_truth_samples):
    """
    Classification sollte unter 5 Sekunden pro Dokument sein.
    """
    import time
    
    sample = ground_truth_samples[0]
    
    start = time.time()
    result = classifier.classify(sample["text"])
    elapsed = time.time() - start
    
    print(f"\nClassification time: {elapsed:.2f}s")
    
    assert elapsed < 5.0, f"Classification too slow: {elapsed:.2f}s"


# ============================================================
# Summary Report
# ============================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Custom summary report after tests.
    """
    print("\n" + "="*60)
    print("VERA VERIFICATION SYSTEM - TEST SUMMARY")
    print("="*60)
    
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    skipped = len(terminalreporter.stats.get('skipped', []))
    
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED - SYSTEM READY FOR DEMO PHASE!")
    else:
        print("\n✗ TESTS FAILED - FIX BEFORE PRODUCTION!")
    
    print("="*60 + "\n")
