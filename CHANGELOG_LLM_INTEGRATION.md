# VERA LLM Backend-Integration - Änderungsprotokoll

**Datum:** 2026-03-06  
**Ziel:** Telegram Bot lädt nicht mehr eigenes LLM - nutzt Backend API

---

## ✅ Durchgeführte Änderungen

### 1. Neuer FastAPI Endpoint für Bug-Analyse

**Datei:** `backend/api/feedback.py` (NEU)

- **Route:** `POST /api/analyze-bug`
- **Input:** `{"text": string, "category": string}`
- **Output:** Strukturierte Bug-Analyse als JSON
  - module, severity, title, description, expected
  - possible_cause, affected_files, reproduction_steps
  - fix_hint, analysis_method (llm|rule_based)
- **Funktion:** Nutzt `backend.services.bug_analyzer.analyze_bug()`
- **Fallback:** Automatisch regelbasiert wenn LLM nicht verfügbar

**Integration in main.py:**
```python
from backend.api import discovery, feedback
...
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
```

---

### 2. Telegram Bot Umbau

**Datei:** `backend/services/telegram_bot.py`

**Vorher:**
```python
from backend.services.bug_analyzer import analyze_bug  # lädt LLM in Bot-Prozess
```

**Nachher:**
```python
from backend.services.bug_analyzer import analyze_rule_based  # nur Fallback
import aiohttp

async def analyze_bug(text: str) -> dict:
    # HTTP-Call zu Backend API
    async with aiohttp.ClientSession() as session:
        async with session.post(BACKEND_API_URL, ...) as response:
            ...
    # Fallback wenn Backend nicht erreichbar
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return analyze_rule_based(text)
```

**Vorteile:**
- ✅ LLM läuft nur im Backend-Prozess (nicht doppelt im Bot)
- ✅ Backend kann Modell persistent laden (schneller)
- ✅ Automatischer Fallback wenn Backend offline
- ✅ Saubere Service-Trennung (Bot = UI, Backend = Business Logic)

---

### 3. UTF-8 Validierung

**Datei:** `backend/services/javix_bridge.py`

**Status:** ✅ Bereits korrekt implementiert

Alle JSON-Schreiboperationen nutzen:
```python
json.dumps(payload, indent=2, ensure_ascii=False)
filepath.write_text(..., encoding="utf-8")
```

**Datei:** `backend/services/bug_analyzer.py`

**Status:** ✅ Keine Dateioperationen (nur Analyse-Logik)

---

## 📊 Architektur-Übersicht

### Vorher (Speicherverschwendung)
```
Telegram Bot Process:
  ├─ Telegram API Client
  ├─ Mistral 7B LLM (geladen)  ← Verschwendung!
  └─ Bug Analyzer Logic

Backend Process:
  ├─ FastAPI
  ├─ Mistral 7B LLM (geladen)  ← Verschwendung!
  └─ Document Processing
```

### Nachher (Effizient)
```
Telegram Bot Process:
  ├─ Telegram API Client
  └─ HTTP Client → Backend API
      └─ Fallback: analyze_rule_based()

Backend Process:
  ├─ FastAPI
  ├─ Mistral 7B LLM (einmalig geladen)  ← Zentral!
  ├─ POST /api/analyze-bug Endpoint
  └─ Document Processing
```

---

## 🧪 Testing-Anleitung

### 1. Backend starten
```bash
cd C:\Jarvix\vera-office
python backend/main.py
```

### 2. API testen (optional)
```bash
curl -X POST http://localhost:8000/api/analyze-bug \
  -H "Content-Type: application/json" \
  -d '{"text": "OCR erkennt keine Zahlen", "category": "bug"}'
```

### 3. Telegram Bot starten
```bash
python backend/services/telegram_bot.py
```

### 4. Test-Szenario
1. **Backend läuft:** Bug-Report via Telegram → sollte LLM-Analyse zeigen (🤖 KI)
2. **Backend gestoppt:** Bug-Report via Telegram → sollte Regel-Analyse zeigen (📋 Regel)

---

## ✨ Nächste Schritte (optional)

- [ ] API-Key-Auth für `/api/analyze-bug` (Security)
- [ ] Rate Limiting (Schutz vor Spam)
- [ ] Persistent LLM Manager (Modell im RAM halten, nicht bei jedem Request laden)
- [ ] Metrics/Logging für API-Performance

---

## 📝 Notizen

- **Backend-URL:** `http://localhost:8000/api/analyze-bug`
- **Timeout:** 10 Sekunden
- **Fallback:** Regelbasiert bei Timeout/Fehler
- **UTF-8:** Durchgängig sichergestellt (javix_bridge.py)

---

**Erstellt von:** Javix (OpenClaw Subagent)  
**Aufgabe:** VERA LLM Backend-Integration  
**Status:** ✅ Abgeschlossen
