# VERA Verification System - Integration Guide

## Quick Integration (5 Minutes)

### Step 1: Register API Routers in main.py

Add these lines after the existing `app.include_router()` statements (around line 388):

```python
# === VERIFICATION SYSTEM APIs ===
from backend.api import demo_classification, monitoring

app.include_router(demo_classification.router, prefix="/api", tags=["Demo Classification"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])
```

**Full context:**
```python
# Existing routers
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
# ... (other routers)

# ADD THESE TWO LINES:
from backend.api import demo_classification, monitoring
app.include_router(demo_classification.router, prefix="/api", tags=["Demo Classification"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])
```

### Step 2: Verify API Registration

```bash
# Start server
uvicorn backend.main:app --reload

# Test endpoints
curl http://localhost:8000/api/monitoring/health
curl http://localhost:8000/api/monitoring/stats
```

**Expected:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-28T17:30:00",
  "components": {
    "classifier": "ok",
    "rag": "ok",
    "feedback_store": "ok"
  }
}
```

### Step 3: Run Verification

```bash
python backend/run_verification.py
```

**Expected Output:**
```
[1/5] Checking dependencies...
  ✓ pytest installed
[2/5] Running tests...
  ✓ 8 passed
...
✅ ALL CHECKS PASSED - Ready for testing!
```

---

## Full Integration Checklist

### Backend (Already Done ✅)

- [x] Test suite created (`tests/test_vera_classification.py`)
- [x] Ground truth dataset (`tests/fixtures/ground_truth.json`)
- [x] Safe Classifier (`core/ai/safe_classifier.py`)
- [x] Demo API (`api/demo_classification.py`)
- [x] Monitoring API (`api/monitoring.py`)
- [ ] Register routers in `main.py` ← **DO THIS NOW**

### Frontend (TODO)

- [ ] Demo Verification View (`frontend/src/views/DemoVerificationView.vue`)
- [ ] Monitoring Dashboard (`frontend/src/views/MonitoringView.vue`)
- [ ] Navigation links (Admin area)

### Database (Optional)

- [ ] Create `demo_log` table for tracking
- [ ] Create `demo_feedback` table for user corrections

**SQL:**
```sql
-- Demo Log (Classification Tracking)
CREATE TABLE demo_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    prediction TEXT NOT NULL,
    confidence REAL NOT NULL,
    needs_review BOOLEAN NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

-- Demo Feedback (User Corrections)
CREATE TABLE demo_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id INTEGER NOT NULL,
    prediction TEXT NOT NULL,
    correct_class TEXT NOT NULL,
    was_correct BOOLEAN NOT NULL,
    comment TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);

-- Indexes
CREATE INDEX idx_demo_log_doc ON demo_log(doc_id);
CREATE INDEX idx_demo_feedback_doc ON demo_feedback(doc_id);
CREATE INDEX idx_demo_log_timestamp ON demo_log(timestamp);
```

---

## API Endpoints Reference

### Demo Classification

#### POST `/api/demo/classify`
Classify document and request user review.

**Query Params:**
- `doc_id` (int, required): Document ID

**Response:**
```json
{
  "doc_id": 123,
  "prediction": "checkliste",
  "confidence": 0.92,
  "needs_review": false,
  "suggestion": null,
  "reasoning": "Hohe Ähnlichkeit zu bekannten Checklisten",
  "message": "✓ Klassifiziert als 'checkliste' (92%). Bitte bestätigen."
}
```

#### POST `/api/demo/feedback`
Submit user feedback on classification.

**Body:**
```json
{
  "doc_id": 123,
  "correct_class": "checkliste",
  "was_correct": true,
  "comment": "Korrekt erkannt"
}
```

**Response:**
```json
{
  "success": true,
  "message": "✓ Bestätigt: 'Checkliste'"
}
```

#### GET `/api/demo/stats`
Get demo phase statistics.

**Response:**
```json
{
  "total_classified": 45,
  "user_confirmations": 38,
  "user_corrections": 7,
  "accuracy": 0.844,
  "avg_confidence": 0.87,
  "low_confidence_docs": 5,
  "pending_review": 5
}
```

---

### Monitoring

#### GET `/api/monitoring/stats`
Real-time classification statistics.

**Response:**
```json
{
  "classified_today": 45,
  "user_corrections": 3,
  "error_rate": 0.067,
  "avg_confidence": 0.87,
  "low_confidence_docs": 5,
  "pending_review": 5,
  "alerts": [
    "⚠️ VIELE UNSICHERE KLASSIFIKATIONEN: 5 Dokumente benötigen Review"
  ],
  "category_stats": {
    "checkliste": 12,
    "arbeitsanweisung": 8,
    "hygieneplan": 5
  }
}
```

#### GET `/api/monitoring/health`
System health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-28T17:30:00",
  "components": {
    "classifier": "ok",
    "rag": "ok",
    "feedback_store": "ok"
  }
}
```

#### POST `/api/monitoring/alert/test`
Test alert system.

**Response:**
```json
{
  "success": true,
  "message": "Test-Alert gesendet"
}
```

---

## Testing After Integration

### 1. Unit Tests
```bash
# Quick test
pytest tests/ -v

# With coverage
pytest tests/ --cov=backend.core.ai --cov-report=html
```

### 2. API Tests
```bash
# Health check
curl http://localhost:8000/api/monitoring/health

# Get stats
curl http://localhost:8000/api/monitoring/stats

# Test classification (replace doc_id)
curl -X POST "http://localhost:8000/api/demo/classify?doc_id=1"

# Submit feedback
curl -X POST "http://localhost:8000/api/demo/feedback" \
  -H "Content-Type: application/json" \
  -d '{"doc_id":1,"correct_class":"checkliste","was_correct":true}'
```

### 3. End-to-End Test
```bash
# Run full verification
python backend/run_verification.py --full
```

---

## Troubleshooting

### Issue: API endpoints not found (404)

**Cause:** Routers not registered in `main.py`

**Fix:**
```python
# Add to main.py (line ~388)
from backend.api import demo_classification, monitoring
app.include_router(demo_classification.router, prefix="/api", tags=["Demo Classification"])
app.include_router(monitoring.router, prefix="/api", tags=["Monitoring"])
```

### Issue: Import errors

**Cause:** Safe classifier or monitoring module not found

**Fix:**
```bash
# Check if files exist
ls backend/core/ai/safe_classifier.py
ls backend/api/demo_classification.py
ls backend/api/monitoring.py

# Restart server
uvicorn backend.main:app --reload
```

### Issue: Tests fail

**Cause:** RAG index empty or LLM not available

**Fix:**
```bash
# Check system
python backend/run_verification.py

# Build RAG index if needed
python -c "from backend.core.rag_engine import RAGEngine; rag = RAGEngine(); rag.index_documents(force=True)"
```

---

## Next Steps After Integration

1. ✅ Register APIs in main.py
2. ✅ Test endpoints
3. ⏳ Build Frontend Views
4. ⏳ Start Demo-Phase (100 docs)
5. ⏳ Production Deployment

See `VERIFICATION_CHECKLIST.md` for complete roadmap.
