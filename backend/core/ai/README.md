# VERA Office - AI Module

Intelligente Dokumentenverarbeitung mit Mistral 7B.

## Module

### llm_manager.py
Singleton für LLM (Mistral 7B GGUF via llama-cpp-python).

```python
from backend.core.ai import llm

# Check availability
if llm.is_available():
    # Generate completion
    response = llm.generate(
        prompt="<s>[INST] Classify this document... [/INST]",
        max_tokens=300,
        temperature=0.1
    )
```

### classifier.py
Klassifiziert Dokumente mit Dynamic Few-Shot Learning.

```python
from backend.core.ai import classifier

# Classify document
result = classifier.classify(
    ocr_text="Rechnung vom 21.02.2026...",
    categories=[
        {"name": "rechnung", "description": "Rechnungen"},
        {"name": "vertrag", "description": "Verträge"}
    ]
)

# Result: {category, confidence, reasoning, available}
print(f"Category: {result['category']}")
print(f"Confidence: {result['confidence']:.2f}")
```

### namer.py
Generiert semantische Dateinamen.

```python
from backend.core.ai import namer

filename = namer.generate_filename(
    ocr_text="Rechnung Müller Dental 21.02.2026",
    category="rechnung_eingang",
    original_filename="scan_001.pdf"
)

# Result: "2026-02-21_rechnung_eingang_Mueller_Dental.pdf"
```

### filer.py
Organisiert Dokumente automatisch.

```python
from backend.core.ai import filer

# File document (creates folders automatically)
new_path = filer.file_document(
    source_path="/data/documents/temp.pdf",
    category="rechnung_eingang",
    document_date=datetime(2026, 2, 21)
)

# Result: /data/documents/rechnung_eingang/2026/02/temp.pdf
```

### feedback_store.py
Speichert User-Feedback für Continuous Learning.

```python
from backend.core.ai import feedback_store

# Add user correction
feedback_store.add_feedback(
    ocr_text="Rechnung vom...",
    category="rechnung_eingang",
    confirmed_by_user=True,
    confidence=0.95
)

# Get similar examples (for few-shot)
examples = feedback_store.get_similar_examples(
    ocr_text="Neue Rechnung...",
    n=5
)

# Get learning stats
stats = feedback_store.get_category_stats()
# {"rechnung_eingang": 42, "vertrag": 18, ...}
```

## Configuration (vera.yaml)

```yaml
ai:
  model_path: models/mistral-7b-instruct-v0.3.Q4_K_M.gguf
  n_ctx: 4096
  n_threads: 4
  temperature: 0.1
  confidence_threshold: 0.80  # Auto-file threshold
  auto_confirm_threshold: 0.95  # Auto-feedback threshold
  few_shot_examples: 5
```

## Graceful Degradation

Alle Module funktionieren auch **ohne** LLM:

- `classifier`: Gibt `category='unknown'` zurück
- `namer`: Nutzt Fallback-Pattern (Timestamp)
- `feedback_store`: Funktioniert immer (pure SQL + TF-IDF)

Check: `llm.is_available()` → `True` wenn ready

## Database Schema

Feedback Store nutzt SQLite-Tabelle:

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    ocr_snippet TEXT NOT NULL,
    category TEXT NOT NULL,
    confirmed_by_user BOOLEAN DEFAULT 0,
    auto_confirmed BOOLEAN DEFAULT 0,
    confidence REAL,
    weight REAL DEFAULT 1.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Performance

- **Model Load:** ~3-5 Sekunden (einmalig beim Start)
- **Classification:** ~2-4 Sekunden (je nach Textlänge)
- **Few-Shot Lookup:** <100ms (TF-IDF in-memory)
- **File Operations:** <50ms

## Logs

Alle Module nutzen `loguru`:

```
INFO - LLM model loaded successfully
INFO - Klassifikation: rechnung_eingang (Confidence: 0.92)
INFO - Dateiname: 2026-02-21_rechnung_eingang_Mueller.pdf
INFO - Abgelegt in: data/documents/rechnung_eingang/2026/02/
INFO - Feedback added: category=rechnung_eingang, user_confirmed=True
```

## Error Handling

- LLM nicht verfügbar → `llm.is_available() == False`
- Klassifikation fehlgeschlagen → `category='unknown', confidence=0.0`
- Model-Datei fehlt → Log-Warning, Features disabled
- Invalid JSON von LLM → Fallback-Parsing (Textsuche)

Keine Crashes, immer graceful degradation!
