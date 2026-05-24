# VERA Verification System - Test Suite

**Purpose:** Sicherstellen dass VERA funktioniert BEVOR Production!  
**Problem:** "2000 Dokumente falsch klassifiziert!" - Boris  
**Solution:** Test-First Development + Demo-Phase + Monitoring

---

## Quick Start

### 1. Install Dependencies
```bash
pip install pytest pytest-cov
```

### 2. Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test category
pytest tests/ -v -m unit
pytest tests/ -v -m classifier
pytest tests/ -v -m rag
pytest tests/ -v -m feedback

# With coverage
pytest tests/ --cov=backend.core.ai --cov-report=html
```

### 3. Check Results
```bash
# Test report
cat test-report.txt

# Coverage report
open htmlcov/index.html
```

---

## Test Categories

### 🔬 Unit Tests (`-m unit`)
Fast, isolated tests for individual components.

**Examples:**
- Ground truth dataset validation
- Category coverage check
- Model initialization

### 🤖 Classifier Tests (`-m classifier`)
Classification accuracy and confidence thresholds.

**Critical Tests:**
- `test_classification_accuracy` - MUST be >= 85%!
- `test_confidence_threshold` - Low confidence = Review required
- `test_feedback_improves_classification` - Learning works

### 🧠 RAG Tests (`-m rag`)
Retrieval-Augmented Generation context delivery.

**Critical Tests:**
- `test_rag_delivers_context` - RAG must find relevant docs
- `test_rag_index_not_empty` - Index must be populated

### 🔄 Feedback Tests (`-m feedback`)
User feedback storage and retrieval.

**Critical Tests:**
- `test_feedback_storage` - Corrections are saved
- `test_feedback_improves_classification` - Learning loop works

### 🚀 Integration Tests (`-m integration`)
End-to-end pipeline tests (slow but comprehensive).

**Example:**
- `test_full_classification_pipeline` - RAG → Classifier → Result

---

## Ground Truth Dataset

**Location:** `tests/fixtures/ground_truth.json`

**Structure:**
```json
{
  "samples": [
    {
      "id": 1,
      "filename": "checkliste_datenschutz.pdf",
      "type": "checkliste",
      "text": "Checkliste Datenschutz...",
      "keywords": ["checkliste", "datenschutz", "verantwortlich"]
    }
  ],
  "metadata": {
    "total_samples": 30,
    "distribution": {
      "checkliste": 7,
      "arbeitsanweisung": 5,
      ...
    }
  }
}
```

**Categories Covered:**
- ✅ Checkliste (7 samples)
- ✅ Arbeitsanweisung (5 samples)
- ✅ Hygieneplan (3 samples)
- ✅ Freigabeprotokoll (4 samples)
- ✅ Wartungsprotokoll (4 samples)
- ✅ Einweisung (3 samples)
- ✅ Gefährdungsbeurteilung (3 samples)
- ✅ Sonstige (4 samples)

**Total:** 30 samples (Target: 50-100)

---

## Success Criteria

### ✅ PASS Criteria
- **Accuracy:** >= 85% on ground truth
- **RAG Context:** Delivers relevant results (score >= 0.7)
- **Confidence Threshold:** Works correctly (low confidence = review)
- **Feedback Loop:** Stores and retrieves corrections
- **Performance:** < 5 seconds per classification

### ❌ FAIL Criteria
- Accuracy < 85%
- RAG delivers no context
- Confidence threshold not working
- Feedback not stored
- Critical exceptions

---

## How to Add Tests

### 1. Create Test File
```python
# tests/test_my_feature.py
import pytest

@pytest.mark.unit
def test_my_feature():
    """Test description"""
    # Arrange
    expected = "value"
    
    # Act
    result = my_function()
    
    # Assert
    assert result == expected
```

### 2. Run New Test
```bash
pytest tests/test_my_feature.py -v
```

### 3. Add to CI Pipeline (future)
```yaml
# .github/workflows/tests.yml
- name: Run Tests
  run: pytest tests/ --cov=backend --cov-report=xml
```

---

## Ground Truth Expansion

### How to Add Samples

1. **Collect Real Documents:**
   - Export from VERA (Praxis-Dokumente)
   - Anonymize sensitive data
   - OCR Text extrahieren

2. **Manual Annotation:**
   - Lese Dokument
   - Bestimme korrekte Kategorie
   - Dokumentiere Reasoning

3. **Add to ground_truth.json:**
```json
{
  "id": 31,
  "filename": "new_document.pdf",
  "type": "arbeitsanweisung",
  "text": "OCR text here...",
  "keywords": ["keyword1", "keyword2"]
}
```

4. **Run Tests:**
```bash
pytest tests/test_vera_classification.py::test_classification_accuracy -v
```

---

## Debugging Failed Tests

### Test Failed: Accuracy < 85%

**Possible Causes:**
1. RAG Index leer/schlecht
2. Classifier Prompt nicht optimal
3. Ground Truth fehlerhaft

**Actions:**
```bash
# Check RAG index
pytest tests/ -v -m rag

# Check which samples failed
pytest tests/test_vera_classification.py::test_classification_accuracy -v -s

# Improve classifier prompt
# Edit: backend/core/ai/classifier.py
```

### Test Failed: RAG delivers no context

**Possible Causes:**
1. ChromaDB collection leer
2. Embeddings nicht erstellt
3. Search Query fehlerhaft

**Actions:**
```bash
# Check RAG collection
pytest tests/ -v -k "rag_index"

# Re-index documents
python -c "from backend.core.rag_engine import RAGEngine; rag = RAGEngine(); rag.index_documents(force=True)"
```

### Test Failed: Feedback not stored

**Possible Causes:**
1. Database nicht initialisiert
2. Feedback-Tabelle fehlt
3. Permissions

**Actions:**
```bash
# Check feedback store
pytest tests/ -v -k "feedback_storage"

# Check database
sqlite3 data/vera.db ".schema feedback"
```

---

## Continuous Improvement

### After Each Demo-Phase Week

1. **Collect Metrics:**
   - Accuracy: X%
   - Fehlerrate: Y%
   - Low-Confidence: Z docs

2. **Analyze Failures:**
   - Welche Kategorien problematisch?
   - Häufige Fehler?
   - Neue Ground-Truth Samples nötig?

3. **Improve System:**
   - Prompt tuning
   - Few-shot examples erweitern
   - RAG index mit neuen Docs

4. **Re-Run Tests:**
```bash
pytest tests/ -v --cov=backend.core.ai
```

5. **Update Ground Truth:**
   - Add problematic cases
   - Verify improvements

---

## Integration with CI/CD (Future)

```yaml
# .github/workflows/vera-tests.yml
name: VERA Classification Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=backend.core.ai --cov-report=xml
    
    - name: Check accuracy
      run: |
        # Fail if accuracy < 85%
        python scripts/check_accuracy.py
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## FAQ

### Q: Wie viele Ground-Truth Samples brauchen wir?
**A:** Minimum 30 (aktuell), Target 50-100 für robuste Validierung.

### Q: Müssen wir alle Tests bestehen?
**A:** JA! Besonders `test_classification_accuracy` ist kritisch.

### Q: Wie oft Tests ausführen?
**A:** 
- Während Development: Nach jedem Code-Change
- Demo-Phase: Täglich
- Production: Bei jedem Deployment

### Q: Was wenn ein Test fehlschlägt?
**A:** 
1. Log lesen und Ursache finden
2. Bug fixen ODER Ground-Truth korrigieren
3. Test erneut ausführen
4. Erst nach PASS weiter

### Q: Kann man Tests überspringen?
**A:** NEIN! Tests sind der Quality Gate. Kein PASS = Kein Production!

---

## Contact

**Fragen?** Boris Reimers / Javix  
**Issues?** Check `VERIFICATION_CHECKLIST.md` für Troubleshooting
