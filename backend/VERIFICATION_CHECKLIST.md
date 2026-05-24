# VERA Verification Checklist - Production Readiness

**STATUS:** 🟡 In Progress  
**ERSTELLT:** 2026-03-28  
**ZIEL:** VERA sicher in Production bringen - KEINE stillen Fehler mehr!

---

## Phase 1: Test-First Development ✅

### 1.1 Test Suite
- [x] `pytest.ini` erstellt
- [x] `tests/__init__.py` erstellt
- [x] `tests/test_vera_classification.py` implementiert
  - [x] RAG delivers context test
  - [x] Classification accuracy test (85%+ required)
  - [x] Confidence threshold test
  - [x] Feedback loop test
  - [x] Integration test
- [ ] Tests ausführen: `pytest tests/ -v`
- [ ] Alle Tests bestehen

### 1.2 Ground Truth Dataset
- [x] `tests/fixtures/ground_truth.json` erstellt
- [x] 30 manuell annotierte Samples
- [x] Alle wichtigen Kategorien abgedeckt:
  - Checkliste (7 samples)
  - Arbeitsanweisung (5 samples)
  - Hygieneplan (3 samples)
  - Freigabeprotokoll (4 samples)
  - Wartungsprotokoll (4 samples)
  - Einweisung (3 samples)
  - Gefährdungsbeurteilung (3 samples)
  - Sonstige (4 samples)
- [ ] Erweitern auf 50+ Samples (Target: 100)

### 1.3 Accuracy Benchmark
- [ ] Initial Test-Run durchführen
- [ ] Accuracy dokumentieren (Baseline)
- [ ] Target: 85%+ Accuracy
- [ ] Bei < 85%: Classifier verbessern (Prompt, Few-Shot, RAG)

---

## Phase 2: Safe Classification System ✅

### 2.1 Confidence-Based Classifier
- [x] `core/ai/safe_classifier.py` implementiert
- [x] Confidence Threshold: 0.85 (85%)
- [x] Bei Low Confidence: "UNBEKANNT" + needs_review=True
- [x] Suggestion für User anzeigen
- [ ] Threshold konfigurierbar machen (Admin-Panel)

### 2.2 RAG Integration
- [x] RAG Engine in Safe Classifier integriert
- [ ] RAG Index aufbauen (aus bestehenden QM-Dokumenten)
- [ ] RAG Index Quality testen
- [ ] Min. 100 Dokumente im Index

### 2.3 Feedback Store
- [x] feedback_store.py bereits vorhanden
- [x] TF-IDF für Similar Search
- [x] User Feedback mit weight=2.0
- [ ] Migration von alten Feedback-Daten (falls vorhanden)

---

## Phase 3: Demo-Phase Workflow ✅

### 3.1 Demo Classification API
- [x] `api/demo_classification.py` implementiert
- [x] POST `/api/demo/classify` - Klassifiziere Dokument
- [x] POST `/api/demo/feedback` - User-Feedback speichern
- [x] GET `/api/demo/stats` - Demo-Statistiken
- [ ] In `main.py` registrieren
- [ ] API testen (Postman/curl)

### 3.2 Demo Database
- [ ] `demo_log` Tabelle erstellen (für Tracking)
  ```sql
  CREATE TABLE demo_log (
      id INTEGER PRIMARY KEY,
      doc_id INTEGER NOT NULL,
      prediction TEXT NOT NULL,
      confidence REAL NOT NULL,
      needs_review BOOLEAN NOT NULL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  ```
- [ ] `demo_feedback` Tabelle erstellen
  ```sql
  CREATE TABLE demo_feedback (
      id INTEGER PRIMARY KEY,
      doc_id INTEGER NOT NULL,
      prediction TEXT NOT NULL,
      correct_class TEXT NOT NULL,
      was_correct BOOLEAN NOT NULL,
      comment TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  ```

### 3.3 Demo-Phase Planung
- [ ] Ziel: 100 Dokumente mit User-Feedback
- [ ] Timeline: 1-2 Wochen Demo-Phase
- [ ] Team-Schulung: Wie funktioniert Demo-Mode?
- [ ] Daily Check: Stats-Dashboard prüfen

---

## Phase 4: Monitoring System ✅

### 4.1 Monitoring API
- [x] `api/monitoring.py` implementiert
- [x] GET `/api/monitoring/stats` - Real-Time Stats
- [x] GET `/api/monitoring/health` - System Health
- [x] POST `/api/monitoring/alert/test` - Test Alert
- [ ] In `main.py` registrieren
- [ ] API testen

### 4.2 Alert System
- [x] Alert-Logik implementiert:
  - Fehlerrate > 10%
  - Viele Low-Confidence Docs
  - Niedrige Avg Confidence
- [ ] Telegram-Integration (alert an Boris)
- [ ] Email-Integration (optional)
- [ ] Alert-Test durchführen

### 4.3 Monitoring Dashboard (Frontend)
- [ ] `frontend/src/views/MonitoringView.vue` erstellen
- [ ] Real-Time Stats anzeigen
- [ ] Charts für Trends (Chart.js / Apex Charts)
- [ ] Alert-Banner bei Problemen
- [ ] Auto-Refresh (alle 30s)

---

## Phase 5: Frontend Integration

### 5.1 Demo Verification View
- [ ] `frontend/src/views/DemoVerificationView.vue` erstellen
- [ ] Features:
  - Dokument Preview (PDF/Bild)
  - Prediction anzeigen (mit Confidence)
  - "✓ Korrekt" Button
  - "✗ Korrigieren" Dialog mit Kategorie-Auswahl
  - Progress Tracker (Doc X/100)
- [ ] Keyboard Shortcuts (Schnelligkeit!)
  - `C` = Correct
  - `X` = Wrong → Dialog
  - `→` = Next Doc

### 5.2 Monitoring Dashboard View
- [ ] Stats-Cards (Klassifiziert, Korrekturen, Fehlerrate)
- [ ] Confidence-Chart (Avg über Zeit)
- [ ] Category Breakdown (Pie Chart)
- [ ] Alert-Banner (rot bei Problemen)
- [ ] Trend-Graph (7 Tage)

### 5.3 Navigation
- [ ] "Demo-Modus" in Admin-Bereich
- [ ] "Monitoring" in Admin-Bereich
- [ ] Nur für Admin-User sichtbar

---

## Phase 6: Production Deployment

### 6.1 Pre-Production Checks
- [ ] Alle Tests bestehen (pytest)
- [ ] Demo-Phase abgeschlossen (100 Docs)
- [ ] Accuracy >= 85%
- [ ] Fehlerrate <= 10%
- [ ] Keine kritischen Bugs
- [ ] Performance OK (< 5s pro Klassifikation)

### 6.2 Rollout-Strategie
- [ ] Feature-Flag "auto_classification" (default: OFF)
- [ ] Nur aktivieren wenn:
  - Demo-Phase erfolgreich
  - Boris Approval
  - Monitoring aktiv
- [ ] Schrittweise: Erst 10%, dann 50%, dann 100%

### 6.3 Post-Production Monitoring
- [ ] Täglicher Stats-Check (erste 2 Wochen)
- [ ] Wöchentlicher Review-Call mit Boris
- [ ] Alert bei Fehlerrate > 10% (sofort reagieren!)
- [ ] Feedback-Loop weiterhin aktiv (kontinuierliches Lernen)

---

## Success Criteria (PFLICHT!)

✅ **Test Suite:**
- [x] 30+ Ground Truth Samples
- [ ] 85%+ Accuracy auf Tests
- [ ] Alle Tests bestehen

✅ **Safe Classification:**
- [x] Confidence Threshold System implementiert
- [ ] RAG Index aufgebaut
- [ ] < 10% Low-Confidence Docs (nach Training)

✅ **Demo Phase:**
- [x] API implementiert
- [ ] 100 Dokumente mit User-Feedback
- [ ] Accuracy >= 85%

✅ **Monitoring:**
- [x] Real-Time Stats API
- [x] Alert System
- [ ] Dashboard live
- [ ] Telegram-Alerts aktiv

✅ **Frontend:**
- [ ] Demo Verification View
- [ ] Monitoring Dashboard
- [ ] Benutzerfreundlich (30-Sekunden-Regel!)

---

## Blocker & Risks

### 🔴 HIGH PRIORITY
- [ ] **RAG Index leer:** Ohne RAG-Kontext funktioniert Klassifikation schlecht
  - Action: QM-Dokumente indexieren (100+)
- [ ] **LLM nicht verfügbar:** Mistral Model fehlt
  - Action: Model-Path prüfen, ggf. Llama 3 nutzen

### 🟡 MEDIUM PRIORITY
- [ ] **Feedback Store leer:** Wenig Training-Daten
  - Action: Alte Klassifikationen als Feedback migrieren
- [ ] **Performance:** Klassifikation > 5s
  - Action: Model quantization, Batch-Processing

### 🟢 LOW PRIORITY
- [ ] **UI/UX:** Demo-View nicht intuitiv
  - Action: User-Testing mit Team

---

## Timeline

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| 1. Tests | Test Suite + Ground Truth | 1h | ✅ DONE |
| 2. Safe Classifier | Confidence System | 1h | ✅ DONE |
| 3. API | Demo + Monitoring Endpoints | 1h | ✅ DONE |
| 4. Frontend | Views + Charts | 2-3h | 🟡 TODO |
| 5. Integration | Testing + Bugfixes | 1-2h | 🟡 TODO |
| 6. Demo Phase | 100 Docs mit Feedback | 1-2 Wochen | ⏳ WAITING |

**Total Development:** ~6-8h  
**Demo Phase:** 1-2 Wochen  
**Target Production:** Nach erfolgreicher Demo-Phase

---

## Notes

- **Boris' Concern:** "2000 Dokumente falsch klassifiziert!" → LÖSUNG: Confidence-Threshold + Demo-Phase
- **Kein Blind Deploy:** Erst Demo, dann Production
- **Monitoring ist PFLICHT:** Tägliche Checks, Alerts bei Problemen
- **User-Feedback = Training:** Jede Korrektur verbessert das System

---

**NEXT STEPS:**
1. ✅ Test Suite ausführen: `pytest tests/test_vera_classification.py -v`
2. RAG Index aufbauen (100+ QM-Dokumente)
3. Frontend Views implementieren
4. Demo-Phase starten (100 Docs)
5. Production-Readiness Check
