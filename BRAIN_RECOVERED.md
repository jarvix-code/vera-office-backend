# BRAIN.md — VERA Office Sachverständigen-Dokument

> **PFLICHTLEKTÜRE für jeden Sub-Agent vor Arbeit an VERA Office.**
> Zuletzt aktualisiert: 2026-02-22

---

## 0. Warum existiert dieses Projekt?

### Das Produkt
- **VERA Office** = **V**ersatile **E**nterprise **R**ecord **A**ssistant
- Ein On-Premise Dokumenten-Management-System für deutsche KMU (10–50 Mitarbeiter)
- Kernversprechen: **„Post rein, automatisch organisiert, jederzeit auffindbar."**
- Zielgruppe: Kleine Unternehmen mit Dokumentenchaos — Praxen, Handwerk, Büros
- Erster Testkunde: Boris' eigene Zahnarztpraxis (SENZIVO) in Bamberg

### Das Geschäftsmodell
- **Hardware:** Mini-PC beim Kunden (200–400€), läuft im lokalen Netzwerk
- **Software:** Modulares Lizenzmodell
  - 🟢 **VERA Basis** (Pflicht) — Dokumenten-Management (Scan, OCR, Ablage, Suche)
  - 💰 **VERA ERP** (Add-on) — Finanzen, Auswertungen, DATEV-Export
  - 💰 **VERA QM** (Add-on) — Qualitätsmanagement (gesetzlich vorgeschrieben für Praxen)
- **Setup-Gebühr:** 6–12k €
- **Monatliche Lizenz:** je nach Modul-Kombination
- **Vertrieb:** Über Systemhäuser (nach 3–5 erfolgreichen Installationen)

### Was ist Erfolg?
- Messbare Zeitersparnis bei der Dokumentenablage
- Fehlerfreie Klassifikation (>90% Trefferquote)
- Zufriedene Kunden die Module dazukaufen
- Skalierung über Systemhäuser statt Einzelvertrieb

### Deine Rolle als Sub-Agent
- Du baust an einem **PRODUKT**, nicht an einem Hobby-Projekt
- Jede Entscheidung muss dem **Kunden** dienen
- Code-Qualität = Produktqualität = Kundenzufriedenheit
- Wenn du zwischen „technisch elegant" und „für den Kunden besser" wählen musst: **Kunde gewinnt**

### Dein Modul: VERA Basis
> **Du baust die Grundlage auf der alles aufbaut — wenn das nicht funktioniert, kauft niemand Module.**

VERA Basis ist das Pflichtmodul. Jeder Kunde hat es. Wenn die OCR schlecht ist, die Ablage unzuverlässig oder die Suche nichts findet, ist das gesamte Produkt tot. Die Add-on-Module (ERP, QM) setzen auf deiner Arbeit auf — ihre Qualität kann nur so gut sein wie deine Grundlage.

---

## A. Domänenwissen

### Was ist VERA Office?
**V**ersatile **E**nterprise **R**ecord **A**ssistant — ein On-Premise Dokumenten-Management-System für deutsche KMU (10–50 Mitarbeiter). Läuft auf einem Mini-PC (Intel N100/AMD Ryzen, 16GB RAM, 512GB SSD) im lokalen Netzwerk. Erreichbar als PWA über `http://vera-office.local`.

**Kernversprechen:** „Post rein → automatisch organisiert → jederzeit auffindbar."

**Zielgruppe:** Zahnarztpraxen, Handwerk, kleine Büros. Erster Testfall: Boris' Zahnarztpraxis.

### OCR-Pipeline (technisch)

Die komplette Pipeline ist in `backend/main.py::process_new_document()` implementiert:

```
1. Bildverarbeitung (ImageProcessor — OpenCV)
   - Resize auf max 2048px
   - Kantenerkennung (Canny) → 4-Punkt-Perspektivkorrektur
   - CLAHE-Kontrastoptimierung (LAB-Farbraum)
   - Rauschunterdrückung (fastNlMeansDenoising)

2. OCR (OCREngine — PaddleOCR)
   - Sprache: Deutsch, CPU-only
   - Angle Classification aktiviert (gedrehte Dokumente)
   - Konfidenz-Filter: nur Zeilen mit confidence > 0.5
   - Lazy Loading: Engine wird erst beim ersten Aufruf initialisiert

3. PDF-Generierung (PDFGenerator — PyMuPDF/fitz)
   - Bild + OCR-Text als durchsuchbarer Layer

4. KI-Klassifikation (DocumentClassifier → Mistral 7B via llama-cpp-python)
   - Prompt: Instruktions-Format [INST]...[/INST]
   - Few-Shot-Learning: TF-IDF Similarity auf Feedback-Store (bis 5 Beispiele)
   - Kategorien aus YAML-Templates geladen (base.yaml + branchenspezifisch)
   - Output: JSON {category, confidence, reasoning}
   - Fallback: Keyword-Matching wenn LLM nicht verfügbar

5. KI-Namer (DocumentNamer → Mistral 7B)
   - Extrahiert: Datum, Absender, Betreff aus OCR-Text
   - Schema: YYYY-MM-DD_Kategorie_Absender_Betreff.pdf
   - Fallback: YYYY-MM-DD_Kategorie_HHMMSS.pdf

6. Auto-Filing (DocumentFiler)
   - Struktur: documents/kategorie/jahr/monat/datei.pdf
   - Nur wenn confidence >= 0.80 (konfigurierbar)

7. Datenbank-Eintrag (SQLAlchemy → SQLite)

8. Feedback-Store (wenn confidence >= 0.95 → auto-confirm)
   - TF-IDF-Vektorisierung für Few-Shot-Retrieval
   - User-Korrekturen haben weight=2.0

9. Cleanup (Temp + Inbox-Original löschen)
```

### Klassifikation — Wie entscheidet die KI?

**Dreistufig:**
1. **LLM (Mistral 7B Q4_K_M):** Hauptklassifikation via Prompt mit Kategorien-Liste + Few-Shot-Beispielen. Temperature=0.1 für Konsistenz.
2. **Keyword-Fallback:** Wenn LLM nicht geladen → einfaches Keyword-Matching (≥2 Treffer nötig, max 0.7 Konfidenz).
3. **Template Knowledge:** Kategorien werden dynamisch aus YAML-Templates geladen (`backend/data/folder_templates/`), nicht hardcodiert.

**Schwellenwerte:**
- `confidence >= 0.80` → Auto-Filing (Dokument wird automatisch abgelegt)
- `confidence >= 0.95` → Auto-Confirm (Feedback-Eintrag ohne User-Bestätigung)
- `confidence < 0.80` → Rückfrage an User

**Vision-LLM (LLaVA):** Separat für Bild-Qualitätsprüfung (scharf/schief/komplett?). Lazy-loaded.

### Modulares Lizenzsystem

**Zwei parallele Systeme existieren (ACHTUNG — siehe Fallen!):**

#### 1. `license_check.py` — Startup-Check (einfach)
- Liest `data/license.key` als JSON mit `payload` (base64) + `signature` (base64)
- RSA PKCS1v15 + SHA256 Signaturprüfung
- Embedded Public Key im Code
- **Kein Kill-Switch im Betrieb** — nur beim Start
- Ohne Lizenz: Evaluierungsmodus (startet trotzdem)

#### 2. `license.py` — Vollständiges System (komplex)
- RSA-4096 Signatur + AES-256-GCM Verschlüsselung
- Hardware-Binding via Device-Fingerprint (Hostname + MAC + CPU + Disk Serial)
- Trial-Lizenzen: selbst-signiert mit eingebettetem Trial-Key
- Online-Validierung gegen `license.vera-office.de` (mit 30-Tage Grace Period)
- Aktivierung: Online (API), per Datei (.key), oder USB-Stick

**Pläne (plans.py):**
| Plan | Dokumente | Preis/Monat | Features |
|------|-----------|-------------|----------|
| trial | 100 | 0€ | ocr, classify, search, export |
| basic | 5.000 | 29€ | + scanner |
| professional | ∞ | 59€ | + voice, api, multi_user |
| enterprise | ∞ | 99€ | + priority_support, custom_training |

**Schlüssel-Management:**
- Private Key: `backend/core/keys/private_key.pem` (NIEMALS committen!)
- Public Key: `backend/core/keys/public_key.pem` (shipped mit App)
- Tools: `tools/generate_keys.py`, `tools/create_license.py`, `tools/verify_license.py`

### Deutsche KMU-Compliance

**GoBD (Grundsätze ordnungsmäßiger Buchführung):**
- Dezimales Nummerierungsschema nach DIN 6862 in Ordnerstruktur (`base.yaml`)
- Verfahrensdokumentation als eigene Kategorie (10.01)
- Unveränderbarkeit: PDFs mit OCR-Layer, Soft-Delete statt Löschen

**Aufbewahrungsfristen (in YAML-Templates definiert):**
- Rechnungen, Jahresabschlüsse, Steuern: **10 Jahre**
- Personalakten, Lohn, Verträge: **6 Jahre** (nach Ende)
- Bewerbungen: **1 Jahr** (AGG)
- Gesellschaftsdokumente: **Dauerhaft**
- VERA warnt bei Löschversuch wenn Frist nicht abgelaufen

**DATEV:**
- Export-Modul geplant (`backend/export/datev.py` — Stub existiert)
- Konformes Namensschema + Begleitdatei
- DATEV-API-Anbindung erst Phase 2

---

## B. System-Architektur

### Backend-Module

| Modul | Pfad | Aufgabe |
|-------|------|---------|
| **main.py** | `backend/main.py` | FastAPI App, Lifespan, Router-Mounting, SPA-Serving |
| **config.py** | `backend/config.py` | Pydantic Settings + YAML-Overlay (`config/vera.yaml`) |
| **database.py** | `backend/db/database.py` | SQLAlchemy Engine (SQLite, StaticPool), Session-Factory |
| **ImageProcessor** | `backend/core/image_processor.py` | OpenCV: Resize, Perspektive, CLAHE, Denoise |
| **OCREngine** | `backend/core/ocr_engine.py` | PaddleOCR Wrapper (Lazy Loading) |
| **PDFGenerator** | `backend/core/pdf_generator.py` | PyMuPDF: Bild→PDF mit OCR-Layer |
| **LLMManager** | `backend/core/ai/llm_manager.py` | Singleton: Mistral 7B (Text) + LLaVA (Vision) via llama-cpp |
| **DocumentClassifier** | `backend/core/ai/classifier.py` | LLM-Klassifikation + Keyword-Fallback |
| **DocumentNamer** | `backend/core/ai/namer.py` | LLM-basierte Dateibenennung |
| **DocumentFiler** | `backend/core/ai/filer.py` | Auto-Filing in Ordnerstruktur (Kategorie/Jahr/Monat) |
| **FeedbackStore** | `backend/core/ai/feedback_store.py` | TF-IDF Few-Shot-Learning, SQLite-basiert |
| **TemplateKnowledge** | `backend/core/ai/template_knowledge.py` | YAML→Kategorien-Liste, DB-Sync |
| **LicenseService** | `backend/core/license.py` | RSA-4096 + AES-256-GCM Lizenzsystem |
| **license_check** | `backend/core/license_check.py` | Einfacher Startup-Check |
| **HotfolderScanner** | `backend/core/scanner.py` | Watchdog: Überwacht `data/inbox/` |
| **MDNSService** | `backend/core/mdns.py` | Zeroconf: `vera-office.local` im LAN |
| **crypto** | `backend/core/crypto.py` | RSA-Keygen, Signatur, AES-GCM, Device-Fingerprint |

### API-Router

| Router | Prefix | Endpunkte |
|--------|--------|-----------|
| `system` | `/api/system` | Health, Status, Stats, Info |
| `onboarding` | `/api/onboarding` | Wizard Steps 1-5, Status, Reset |
| `documents` | `/api/documents` | Upload, List, Get, Download, Delete, Search |
| `documents_ai` | `/api/documents` | KI-Klassifikation, Re-Classify |
| `agent` | `/api` | Chat (POST /agent/chat), Suggestions, Voice (Stub) |
| `scanner` | — | Scanner-Discovery, Status |
| `folders` | `/api/folders` | Ordnerstruktur-Management |

### Frontend

**Stack:** Vue 3 + TypeScript + Quasar + Pinia + Vite

**Views:**
| View | Route | Funktion |
|------|-------|----------|
| ChatView | `/` (Home) | Chat-Interface mit VERA |
| DashboardView | `/dashboard` | Übersicht, letzte Dokumente |
| DocumentsView | `/documents` | Dokumentenliste mit Filter |
| DocumentDetailView | `/documents/:id` | Einzeldokument + PDF-Viewer |
| CaptureView | `/capture` | Kamera-Erfassung (iPad) |
| SearchView | `/search` | Volltextsuche |
| TasksView | `/tasks` | To-Do-Liste |
| ExportView | `/export` | DATEV/USB/E-Mail Export |
| OnboardingView | `/onboarding` | Ersteinrichtung |
| SettingsView | `/settings` | Einstellungen |

**Stores (Pinia):**
- `documents` — CRUD, Search, Upload
- `onboarding` — Wizard-State, Completion-Check
- `chat` — Chat-Nachrichten, Session

**Navigation Guard:** Alle Views außer Chat und Onboarding erfordern abgeschlossenes Onboarding.

**API-Service:** `frontend/src/services/api.ts` — Axios-basiert

### Datenfluss: Upload → Ablage

```
[iPad/Browser] --POST /api/documents/upload--> [FastAPI]
    |
    v
[data/inbox/] <--HotfolderScanner (Watchdog)--> process_new_document()
    |
    v
[ImageProcessor] → [OCREngine] → [PDFGenerator] → [Classifier] → [Namer] → [Filer]
    |                                                                            |
    v                                                                            v
[data/documents/kategorie/2026/02/datei.pdf]  ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←|
    |
    v
[SQLite: documents-Tabelle] + [FeedbackStore: feedback-Tabelle]
```

### Datenbank-Schema (SQLite)

**Tabelle `documents`:**
- id, filename, original_filename, file_path, file_size, file_hash (SHA256)
- category_id (FK → categories), classification_confidence, classification_reasoning
- ocr_text, ocr_language, ocr_corrected
- document_date, sender, reference_number, amount (extrahierte Metadaten)
- page_count, processed, processing_error
- original_image_path, quality_score, quality_issues
- created_at, updated_at, deleted (Soft Delete), deleted_at

**Tabelle `categories`:**
- id, name (unique), display_name, description
- storage_path, keywords, retention_years
- is_system (nicht löschbar)
- created_at, updated_at
- Relation: documents (1:N)

**Tabelle `settings`:**
- id, key (unique), value (JSON-serialisiert), value_type
- description, category
- created_at, updated_at

**Tabelle `onboarding_state`:**
- id, completed, current_step, total_steps
- company_profile (JSON), document_types (JSON), network_config (JSON), onboarding_chat_data (JSON)
- created_at, updated_at, completed_at

**Tabelle `feedback`** (direkt in SQLite, nicht SQLAlchemy):
- id, ocr_snippet, category, confirmed_by_user, auto_confirmed, confidence, weight, timestamp

### Ordnerstruktur-Templates

Definiert in `backend/data/folder_templates/`:
- `base.yaml` — Universelle KMU-Struktur (11 Hauptkategorien, GoBD-konform)
- `arztpraxis.yaml` — Zahnarzt/Arztpraxis (QM, Hygiene, Labor)
- `handwerk.yaml` — Handwerksbetriebe
- `einzelhandel_gastro.yaml` — Einzelhandel & Gastronomie
- `it_agentur.yaml` — IT & Agenturen
- `steuerberater_ra.yaml` — Steuerberater & Rechtsanwälte
- `allgemein.yaml` — Allgemein

Kategorien werden beim Onboarding aus Base + Branche zusammengeführt und in die DB synchronisiert (`sync_categories_to_db()`).

---

## C. Bekannte Fallen

### 1. Zwei Lizenzsysteme parallel
`license_check.py` (Startup, PKCS1v15) und `license.py` (Runtime, PSS-Padding) verwenden **unterschiedliche Signaturverfahren**. Sie sind NICHT kompatibel. `license_check.py` hat einen eigenen eingebetteten Public Key. Wer am Lizenzsystem arbeitet, muss BEIDE Dateien kennen.

### 2. Trial-Signatur ist Placeholder
`license.py::_create_trial_license_package()` setzt `signature = b"TRIAL-SIGNATURE"` — ein Placeholder. Die Verifizierung beim Laden wird dadurch fehlschlagen. Trial-Lizenzen funktionieren nur, weil der Startup-Check (`license_check.py`) sie durchlässt (kein license.key = Evaluierungsmodus).

### 3. LLM-Loading blockiert den Start
`LLMManager.__init__()` lädt das Modell synchron (~15-30 Sek für Mistral 7B Q4). Das blockiert den FastAPI-Start. Vision-LLM ist lazy (gut), Text-LLM nicht (schlecht).

### 4. PaddleOCR erster Aufruf
Beim ersten OCR-Aufruf lädt PaddleOCR ~200MB Modelle herunter. Offline-Installationen brechen hier ab wenn keine Modelle vorinstalliert sind.

### 5. mDNS unter Windows
`zeroconf` funktioniert unter Windows unzuverlässig. Apple-Geräte (iPad) finden `vera-office.local` nicht immer. Fallback: direkte IP-Adresse.

### 6. SQLite Concurrency
`StaticPool` + `check_same_thread=False` erlaubt Multi-Thread-Zugriff, aber SQLite hat Write-Locks. Bei vielen gleichzeitigen Uploads können `database is locked`-Errors auftreten.

### 7. Feedback-Store: Separate SQLite-Verbindung
`FeedbackStore` öffnet eine eigene `sqlite3.connect()` statt die SQLAlchemy-Session zu nutzen. Zwei unkoordinierte Connections auf dieselbe DB = potentielle Lock-Probleme.

### 8. Hardcoded Pfade
`DocumentFiler` und `FeedbackStore` berechnen `PROJECT_ROOT` relativ zu `__file__`. Bei Docker-Deployment oder Pfadänderungen können diese brechen.

### 9. OCR-Text Truncation
`ocr_text` wird bei 50.000 Zeichen abgeschnitten (DB-Insert), Feedback-Store bei 2.000 Zeichen. Lange Dokumente verlieren Kontext.

### 10. No Migration System
Datenbank nutzt `create_all()` statt Alembic-Migrations. Schemaänderungen auf bestehenden Installationen erfordern manuelles ALTER TABLE oder DB-Reset.

---

## D. Arbeitsprotokoll

### Pflicht-Checkliste VOR Änderungen

- [ ] BRAIN.md gelesen (komplett)
- [ ] Betroffene Dateien GELESEN (nicht angenommen!)
- [ ] `config/vera.yaml` geprüft (Konfigurationswerte die relevant sind)
- [ ] Änderung geplant und begründet
- [ ] Seiteneffekte auf andere Module geprüft (besonders: Pipeline in `main.py`, LLM-Manager Singleton, DB-Schema)

### Pflicht-Checkliste NACH Änderungen

- [ ] Backend startet fehlerfrei: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- [ ] `/health` und `/api/health` antworten mit `200`
- [ ] `/api/system/status` zeigt korrekte Werte
- [ ] Onboarding-Flow funktioniert (wenn betroffen)
- [ ] Dokument-Upload + OCR funktioniert: `POST /api/documents/upload`
- [ ] Dokumentenliste: `GET /api/documents/list`
- [ ] Suche: `GET /api/documents/search/query?q=test`
- [ ] Frontend baut: `cd frontend && npm run build`
- [ ] BRAIN.md aktualisiert (wenn Architektur/Verhalten geändert)

### Was darf NICHT brechen?

1. **Upload-Pipeline** — Kernfunktion. Bild rein → PDF + DB-Eintrag raus.
2. **Onboarding-Wizard** — Ersteinrichtung muss komplett durchlaufen.
3. **Lizenz-Check** — App muss auch OHNE Lizenz starten (Evaluierungsmodus).
4. **Frontend SPA-Routing** — Alle Routes müssen `index.html` liefern (nicht 404).
5. **CORS** — Frontend muss Backend erreichen können (`allow_origins=["*"]`).
6. **Hotfolder-Scanner** — Muss Dateien in `data/inbox/` erkennen und verarbeiten.

### Wie testet man?

```bash
# Backend starten
cd C:\Jarvix\vera-office
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Health Check
curl http://localhost:8000/health

# Dokument hochladen
curl -X POST http://localhost:8000/api/documents/upload -F "file=@test.jpg"

# Dokumente listen
curl http://localhost:8000/api/documents/list?limit=10

# Suche
curl "http://localhost:8000/api/documents/search/query?q=Rechnung"

# Onboarding Status
curl http://localhost:8000/api/onboarding/status

# Lizenz prüfen
python tools/verify_license.py

# Frontend
cd frontend && npm run dev   # Entwicklung
cd frontend && npm run build  # Production Build
```

Existierende Test-Skripte (Projekt-Root):
- `test_ai_setup.py` — KI-Setup prüfen
- `test_license.py` — Lizenzsystem
- `test_llm_classify.py` — LLM-Klassifikation
- `test_onboarding_chat.py` — Onboarding-Chat
- `test_routes.py` — API-Routen
- `test_sprint2.py` — Sprint-2-Features
- `test_chat_detailed.py` — Chat-Details

---

## E. Modul-Katalog

### 🟢 Basis — Dokumenten-Management (immer aktiv)

**Umfang:** Upload, OCR, Klassifikation, Ablage, Suche, Chat, Export-Grundfunktionen

**Backend:**
- `backend/api/documents.py` + `documents_ai.py` — Upload/CRUD/Suche
- `backend/api/onboarding.py` — Ersteinrichtung
- `backend/api/agent.py` — Chat mit VERA
- `backend/api/folders.py` — Ordnerverwaltung
- `backend/api/scanner.py` — Scanner-Discovery
- `backend/core/` — Alle Kern-Module (OCR, Image, PDF, AI, Scanner)

**Frontend:** Alle Views (Dashboard, Documents, Capture, Search, Chat, Tasks, Export, Settings, Onboarding)

**Datenbank:** documents, categories, settings, onboarding_state, feedback

### 💰 ERP — Finanzen (Add-on, ✅ Backend + Frontend implementiert)

**Backend:** `backend/modules/erp/` — Router, Extractor, Calculator, Reports, Models, Schemas
**Frontend:** `frontend/src/views/erp/` — 5 Views (siehe Sektion J)
**Store:** `frontend/src/stores/erp.ts` | **API-Service:** `frontend/src/services/erp-api.ts`

### 💰 QM — Qualitätsmanagement (Add-on, ✅ Backend + Frontend implementiert)

**Backend:** `backend/modules/qm/` — Router, Models, Schemas
**Frontend:** `frontend/src/views/qm/` — 5 Views (siehe Sektion J)
**Store:** `frontend/src/stores/qm.ts` | **API-Service:** `frontend/src/services/qm-api.ts`

---

## F. Modul-System (Plugin-Architektur)

### Überblick

VERA Office verwendet eine Plugin-Architektur für optionale Module. Jedes Modul ist ein eigenständiges Python-Package unter `backend/modules/`, das sich über eine zentrale Registry registriert und per Lizenzschlüssel freigeschaltet wird.

**Kernkomponenten:**
| Datei | Aufgabe |
|-------|---------|
| `backend/modules/base.py` | `VeraModule` ABC + `TabConfig` Dataclass |
| `backend/modules/registry.py` | `ModuleRegistry` Singleton — Registrierung, Mounting, Manifest |
| `backend/modules/license.py` | `LicenseStore` — Ed25519-basierte Offline-Lizenzvalidierung |

### VeraModule Base Class

Jedes Modul erbt von `VeraModule` und implementiert:

```python
class VeraModule(ABC):
    name: str              # "erp", "qm"
    version: str           # Semver
    display_name: str      # "VERA ERP"
    description: str
    icon: str              # Emoji
    required_license: str  # Lizenz-Key, z.B. "erp"

    def get_routes(self) -> list[APIRouter]    # FastAPI Router
    def get_ui_tabs(self) -> list[TabConfig]   # Sidebar-Tabs
    def on_activate(self) -> None              # Lifecycle: Lizenz aktiviert
    def on_deactivate(self) -> None            # Lifecycle: Lizenz entfernt
    def to_manifest(self, licensed: bool) -> dict  # JSON für Frontend
```

`TabConfig` beschreibt einen Sidebar-Tab: `id`, `label`, `icon`, `route`, `order` (Sortierung).

### ModuleRegistry

Singleton, erstellt beim App-Start mit einem `LicenseStore`:

```python
registry = ModuleRegistry(license_store)
registry.register(ErpModule())   # Registriert Modul + feuert on_activate() wenn lizenziert
registry.register(QmModule())
registry.mount_all(app)          # Mountet Routes unter /api/modules/{name}
app.include_router(registry.create_api_router())  # Meta-Endpoints
```

**Meta-Endpoints (vom Registry erzeugt):**
| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/api/modules` | Liste aller Module + Lizenzstatus (Manifest) |
| POST | `/api/modules/license` | Lizenzschlüssel aktivieren |
| DELETE | `/api/modules/license/{module}` | Lizenz deaktivieren |

**Route-Mounting:** Alle Modul-Router landen unter `/api/modules/{name}/...`
- ERP: `/api/modules/erp/dashboard`, `/api/modules/erp/items`, etc.
- QM: `/api/modules/qm/dashboard`, `/api/modules/qm/audits`, etc.

**`module_for_route(path)`** — findet das Modul anhand des Pfads. Basis für Middleware.

### Lizenzsystem (Ed25519, Offline)

**Algorithmus:** Ed25519 (nicht RSA wie das alte System!) — schneller, kürzere Schlüssel.

**Key-Format (Benutzer-sichtbar):**
```
VERA-ERP-eyJtb2Q...-SIGBASE64
```
Aufbau: `VERA-{MODUL}-{base64url_payload.base64url_signatur}` (in 4er-Chunks mit Bindestrichen).

**Payload (JSON):**
```json
{"mod": "erp", "exp": null, "iss": "vera"}
```
- `mod` — Modul-Name (muss mit `required_license` des Moduls matchen)
- `exp` — Ablaufdatum (ISO) oder `null` für unbefristet
- `iss` — Issuer (immer "vera")

**Validierung (komplett offline):**
1. Regex-Match auf `VERA-{MODULE}-{body}`
2. Body entchunken (Bindestriche entfernen) → `payload_b64.sig_b64`
3. Base64url-Decode → `payload_bytes` + `sig_bytes`
4. Ed25519 `verify(sig_bytes, payload_bytes)` mit Public Key
5. Ablaufdatum prüfen (`exp < today` → ungültig)

**LicenseStore:**
- Persistiert als JSON-Datei: `{module_name: license_key}`
- `activate(key)` → validiert + speichert + gibt `(success, message)` zurück
- `is_licensed(module)` → prüft bei jedem Aufruf (Re-Validierung inkl. Ablaufdatum)
- `get_status(module)` → `"active"` | `"expired"` | `"none"`

**Schlüsselgenerierung (Build-Time):**
```python
from backend.modules.license import generate_keypair, create_license_key
priv_pem, pub_pem = generate_keypair()
key = create_license_key(priv_pem, module="erp", expiry=date(2027, 1, 1))
```

### Middleware (Route-Schutz)

Alle Requests auf `/api/modules/{name}/...` müssen durch eine Lizenz-Middleware:
- `registry.module_for_route(path)` ermittelt das Modul
- `registry.is_licensed(module.name)` prüft die Lizenz
- **Keine Lizenz → HTTP 403** ("Modul nicht freigeschaltet")
- Basis-Routes (`/api/documents`, `/api/system`, etc.) sind NICHT betroffen

### Frontend-Integration

**Manifest:** Frontend ruft `GET /api/modules` → erhält Array mit Modul-Manifesten:
```json
[{
  "name": "erp", "displayName": "VERA ERP", "icon": "📊",
  "licensed": true,
  "tabs": [{"id": "erp-dashboard", "label": "Finanzen", "icon": "📊", "route": "/erp/dashboard", "order": 200}]
}]
```

**Geplante Frontend-Komponenten:**
- `ModuleLock.vue` — Overlay für gesperrte Module ("🔒 Modul freischalten")
- `LicenseInput.vue` — Eingabefeld für Lizenzschlüssel
- `moduleGuard` — Vue Router Guard, prüft Lizenz vor Navigation

**Sidebar:** Tabs werden dynamisch aus Manifest generiert. Unlizenzierte Module: sichtbar aber ausgegraut.

### Neues Modul hinzufügen (Schritt-für-Schritt)

1. **Package erstellen:** `backend/modules/{name}/__init__.py`
2. **VeraModule-Subclass** implementieren: `name`, `version`, `required_license`, `get_routes()`, `get_ui_tabs()`
3. **Router** erstellen: `backend/modules/{name}/router.py` mit FastAPI-Endpoints
4. **Models + Schemas** definieren (SQLAlchemy + Pydantic)
5. **Registrierung** in App-Startup: `registry.register(MyModule())`
6. **Lizenzschlüssel** generieren: `create_license_key(priv_pem, module="{name}")`
7. **Frontend-Views** erstellen unter `frontend/src/views/{Name}/`
8. **Frontend-Routing** + Sidebar-Integration über Manifest

### ⚠️ ACHTUNG: Drei Lizenzsysteme!

Es existieren jetzt DREI verschiedene Lizenzsysteme:

| System | Datei | Algorithmus | Zweck |
|--------|-------|-------------|-------|
| Startup-Check | `backend/core/license_check.py` | RSA PKCS1v15 + SHA256 | App-Start (alt) |
| Runtime-System | `backend/core/license.py` | RSA-4096 PSS + AES-256-GCM | Plans/Features (alt) |
| **Modul-System** | `backend/modules/license.py` | **Ed25519** | Modul-Freischaltung (neu) |

Diese sind **NICHT kompatibel**. Das Modul-System ist das neue, korrekte System. Die alten Systeme existieren noch für Basis-Lizenzierung.

---

## G. ERP-Modul (Finanzen)

### Domänenwissen

**Zielgruppe:** Deutsche KMU, die ihre bereits in VERA erfassten Rechnungen auswerten wollen. Kein Ersatz für DATEV oder Steuerberater — eine Brücke dazwischen.

**Fachbegriffe:**
- **BWA (Betriebswirtschaftliche Auswertung):** Vereinfachte GuV — Umsatzerlöse, Aufwandskategorien, Betriebsergebnis. Vergleich Periode vs. Vorperiode.
- **USt-Voranmeldung:** Umsatzsteuer (eingenommen) minus Vorsteuer (bezahlt) = Zahllast. Meldung ans Finanzamt (monatlich oder quartalsweise).
- **Offene Posten (OP):** Unbezahlte Rechnungen mit Fälligkeitsdatum. Ampelsystem: 🟢 >7 Tage, 🟡 ≤7 Tage, 🔴 überfällig.
- **DATEV-Buchungsstapel:** Standard-Importformat für Steuerberater-Software.

### Architektur

**Pfad:** `backend/modules/erp/`

| Datei | Aufgabe |
|-------|---------|
| `__init__.py` | `ErpModule(VeraModule)` — Registrierung, 3 Tabs (Finanzen, Offene Posten, Reports) |
| `router.py` | FastAPI Router — CRUD `/items`, `/dashboard`, `/reports/*`, `/open-items`, `/stats` |
| `extractor.py` | Extraktion von Finanzdaten aus VERA-Dokumenten (OCR → FinancialRecord) |
| `calculator.py` | Aggregationen: Dashboard, BWA, USt-Voranmeldung, Periodenvergleich |
| `reports.py` | Export: CSV (Semikolon-getrennt), DATEV Buchungsstapel (v700, cp1252) |
| `models.py` | SQLAlchemy: `erp_financial_records` Tabelle |
| `schemas.py` | Pydantic: Create/Update/Out, DashboardData, BwaReport, UstReport |

### Datenmodell

**Tabelle `erp_financial_records`:**
- `id`, `document_id` (FK zum VERA-Dokument)
- `direction`: `incoming` (Eingangsrechnung/Kosten) | `outgoing` (Ausgangsrechnung/Umsatz)
- `invoice_number`, `invoice_date`, `due_date`
- `net_amount`, `vat_rate` (%), `vat_amount`, `gross_amount`
- `counterparty` (Lieferant/Kunde), `category`
- `payment_status`: `open` | `paid` | `overdue`
- `payment_date`, `notes`, `created_at`, `updated_at`

### Datenfluss

```
[VERA Dokument (Rechnung)]
    |
    v
[extractor.py] — Klassifikation → Richtung (incoming/outgoing)
    |              extracted_data → Beträge, Datum, Partner
    |              Auto-Berechnung: netto↔brutto, Fälligkeit (+30 Tage default)
    v
[FinancialRecord] — In-Memory Store (TODO: SQLAlchemy Session)
    |
    v
[calculator.py] — Aggregation pro Zeitraum
    |   ├── Dashboard: Revenue, Expenses, Profit, Cashflow, Top Suppliers/Customers
    |   ├── BWA: Umsatzerlöse, Aufwandskategorien, Betriebsergebnis (Netto-basiert)
    |   └── USt: Output-VAT - Input-VAT = Balance (aufgeschlüsselt nach MwSt-Satz)
    v
[router.py] — API Endpoints
    |
    v
[reports.py] — Export
    ├── CSV: Semikolon-getrennt, deutsche Feldnamen
    └── DATEV: Buchungsstapel v700, SKR03 Kontenrahmen, cp1252 Encoding
```

### Extractor-Logik (Wichtig!)

`extract_from_document(doc)` nimmt ein VERA-Dokument-Dict:
- **Richtungserkennung:** Keywords in Klassifikation (`eingang/incoming/lieferant/kosten` → INCOMING)
- **Betragsberechnung:** Wenn nur netto → brutto auto-berechnet. Wenn nur brutto → netto auto-berechnet.
- **Deutsche Zahlenformate:** `1.234,56` wird korrekt geparsed (Punkt=Tausender, Komma=Dezimal)
- **Default-Fälligkeit:** Eingangsrechnungen ohne Fälligkeitsdatum → +30 Tage

### DATEV-Spezifika

**Format:** EXTF Buchungsstapel v700
- **Encoding:** cp1252 (Windows-1252) — NICHT UTF-8!
- **Header:** 2 Zeilen (Formatdeskriptor + Spaltennamen)
- **Berater-/Mandanten-Nr:** Konfigurierbar (Default: 1001/1)
- **Wirtschaftsjahr-Beginn:** Format YYYYMMDD

**Kontenzuordnung (SKR03, vereinfacht):**
- Eingangsrechnung: Aufwandskonto (Soll) → Kreditor (Haben)
- Ausgangsrechnung: Debitor (Soll) → Erlöskonto (Haben)
- Aufwandskonten: `Material→3400, Büro→4930, Miete→4210, Versicherung→4360, ...` (Default: 4900)
- Erlöskonto: 8400 (Erlöse 19% USt)
- Kreditoren: 70000-Bereich (hash-basiert)
- Debitoren: 10000-Bereich (hash-basiert)

**BU-Schlüssel (Automatik-USt):**
- MwSt ≥19% → BU 3
- MwSt ≥7% → BU 2
- Steuerfrei → BU 0

**Belegdatum:** Format TTMM (Tag+Monat, kein Jahr — DATEV-Konvention)

### API-Endpunkte

| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/items` | Liste mit Filtern (direction, status, counterparty, start/end, limit/offset) |
| GET | `/items/{id}` | Einzelner Record |
| POST | `/items` | Neuen Record anlegen (auto-berechnet MwSt/Brutto) |
| PATCH | `/items/{id}` | Update (Status, Fälligkeit, Kategorie, etc.) |
| DELETE | `/items/{id}` | Löschen |
| GET | `/dashboard` | Aggregiertes Dashboard (start/end, Default: Jahresbeginn bis heute) |
| GET | `/reports/bwa` | BWA-Report (start/end required) |
| GET | `/reports/ust` | USt-Voranmeldung (start/end required) |
| GET | `/reports/csv` | CSV-Download |
| GET | `/reports/datev` | DATEV-Buchungsstapel-Download (berater_nr, mandanten_nr) |
| GET | `/open-items` | Offene Posten mit Ampel (direction-Filter) |
| GET | `/stats` | Sidebar-Badge: total, open, overdue |

### UI-Tabs (Sidebar)

| Tab | Route | Order | Inhalt |
|-----|-------|-------|--------|
| 📊 Finanzen | `/erp/dashboard` | 200 | Dashboard mit Charts |
| 📋 Offene Posten | `/erp/open-items` | 210 | OP-Verwaltung mit Ampel |
| 📄 Reports | `/erp/reports` | 220 | BWA, USt, DATEV-Export |

### Bekannte Fallen / Offene Issues

1. **In-Memory Store!** Router verwendet `_records: list[FinancialRecord]` statt DB-Session. Daten gehen bei Neustart verloren. TODO: SQLAlchemy-Session anbinden.
2. **Kreditoren/Debitoren hash-basiert:** `hash(name) % 9999` ist NICHT stabil (Python-Hash ändert sich zwischen Runs wegen PYTHONHASHSEED). Für DATEV-Export ist das problematisch.
3. **SKR03 Mapping vereinfacht:** Nur 8 Aufwandskategorien gemappt. Reale Praxen brauchen mehr.
4. **Keine Bank-Anbindung:** Zahlungsstatus muss manuell gesetzt werden.
5. **Keine automatische Extraktion:** `extractor.py` ist vorbereitet, aber die Integration mit der OCR-Pipeline (automatische Extraktion bei Upload) fehlt noch.

---

## H. QM-Modul (Qualitätsmanagement)

### Domänenwissen

**Kontext:** Qualitätsmanagement in deutschen Zahnarztpraxen, gesetzlich vorgeschrieben (§135a SGB V). Die BLZK (Bayerische Landeszahnärztekammer) definiert den Standard.

**BLZK-Struktur (3 Hauptbereiche, 31+ Module):**
- **Arbeitssicherheit (as_XX):** Gefährdungsbeurteilung, Betriebsanweisungen, Unterweisungen, Arbeitsmedizin, Notfall
- **Qualitätsmanagement (qm_01–qm_31):** Patienten-/Mitarbeiter-/Prozessorientierung, Praxisführung, Qualitätsziele, Bewertung
- **Handbuch (hb_XX):** Gesetze, Verordnungen, Richtlinien

**6 Grundelemente (QM-Richtlinie G-BA):**
1. Patientenorientierung
2. Mitarbeiterorientierung
3. Prozessorientierung
4. Führung und Verantwortung
5. Fehlerkultur
6. Kommunikation

**Kritische Module (BLZK-Pflicht):** Hygienemanagement (qm_09), Sterilisation (qm_10), Röntgen (qm_12), Datenschutz (qm_15), Gefährdungsbeurteilung (as_01), Notfallmanagement (as_05)

**Audit-Prozess:** Internes Audit mit Fragen pro Grundelement → Ja/Nein/Überspringen → Findings (Mängel) → Maßnahmen → Compliance-Rate

### Architektur

**Pfad:** `backend/modules/qm/`

| Datei | Aufgabe |
|-------|---------|
| `__init__.py` | `QmModule(VeraModule)` — Registrierung, 5 Tabs |
| `router.py` | FastAPI Router — Dashboard, Documents, Handbook, Audits, Hygiene, Compliance, Stats |
| `models.py` | Dataclasses: QMDocument, Audit, HygieneProtocol, ComplianceCheck, Revision |
| `schemas.py` | Pydantic: CRUD-Schemas für alle Entitäten |

### Datenmodell (In-Memory Dataclasses)

**QMDocument:**
- `id`, `title`, `main_area` (Arbeitssicherheit/QM/Handbuch)
- `content`, `status` (Entwurf → Prüfung → Freigegeben → Veraltet → Archiviert)
- `current_version` (Semver), `revisions[]` (Versionshistorie)
- `grundelemente[]`, `tags[]` (Verknüpfung zu Handbuch-Kapiteln)
- `approved_by`, `approved_at`

**Audit:**
- `id`, `title`, `auditor`
- `questions[]` (10 Default-Fragen aus 6 Grundelementen)
- `status` ("In Bearbeitung" → "Abgeschlossen")
- `completion_percentage` (auto-berechnet)
- `findings[]`, `actions[]` (generiert bei Finalisierung aus "Nein"-Antworten)

**HygieneProtocol:**
- `id`, `title`, `area` (z.B. "Behandlungsraum", "Aufbereitung")
- `checklist[]` ({item, checked, timestamp, notes})
- Default-Checkliste: Flächendesinfektion, Instrumente, Handschuhe, Abfall, Sterilisator
- Auto-Close wenn alle Items gecheckt

**ComplianceCheck:**
- `id`, `title`, `category` (Grundelement), `requirement`
- `fulfilled`, `evidence`, `due_date`, `checked_by`

### Datenfluss

```
[QM-Dokumente]
    |
    v
[Erstellen/Bearbeiten] → Versionierung (Minor-Bump bei Content-Änderung)
    |                    → Revisions-Historie mit Changelog
    v
[Status-Workflow: Entwurf → Prüfung → Freigegeben]
    |
    v
[Handbuch-Kapitel] ← Verknüpfung über Tags
    |
    v
[Audits] → Fragen beantworten → Finalisieren → Findings + Maßnahmen
    |
    v
[Compliance-Checks] → Erfüllungsgrad pro Grundelement
    |
    v
[Dashboard] → Übersicht: Dokumente, Audits, Hygiene, Compliance-Rate, Handbuch-Fortschritt
```

### Handbuch-Struktur

Statisch geseedet mit 13 Kapiteln in 3 Bereichen:
- **as (Arbeitssicherheit):** Gefährdungsbeurteilung, Betriebsanweisungen, Unterweisungen
- **qm (Qualitätsmanagement):** QM-Politik, Organisation, Patientenversorgung, Mitarbeiter, Fehlermanagement, Beschwerdemanagement, Notfall, Kommunikation, Hygiene & Aufbereitung
- **hb (Handbuch):** Praxishandbuch Allgemein

Kapitel können mit QM-Dokumenten verknüpft werden (über Tags).

### API-Endpunkte

| Methode | Pfad | Funktion |
|---------|------|----------|
| GET | `/dashboard` | Übersicht: Dokumente, Audits, Hygiene, Compliance, Handbuch |
| GET/POST | `/documents` | QM-Dokumente CRUD |
| GET/PATCH/DELETE | `/documents/{id}` | Einzeldokument (Patch = Versionierung!) |
| GET | `/handbook` | Handbuch-Struktur nach Bereichen |
| GET | `/handbook/{chapter_id}` | Kapitel + verknüpfte Dokumente |
| GET/POST | `/audits` | Audit-Liste / Neues Audit (mit Default-Fragen) |
| GET/DELETE | `/audits/{id}` | Audit-Details / Löschen |
| PUT | `/audits/{id}/answer/{question_id}` | Frage beantworten |
| POST | `/audits/{id}/finalize` | Audit abschließen → Findings generieren |
| GET | `/audits/{id}/report` | Audit-Report (nach Kategorien) |
| GET/POST | `/hygiene` | Hygieneprotokolle |
| GET | `/hygiene/{id}` | Protokoll-Details |
| PUT | `/hygiene/{id}/check` | Checklisten-Item abhaken |
| GET/POST/PATCH/DELETE | `/compliance` | Compliance-Checks CRUD |
| GET | `/stats` | Sidebar-Badge: open_audits, open_hygiene, unfulfilled_compliance |

### UI-Tabs (Sidebar)

| Tab | Route | Order | Inhalt |
|-----|-------|-------|--------|
| 📋 QM Übersicht | `/qm/dashboard` | 300 | Dashboard mit Stats |
| 📖 QM-Handbuch | `/qm/handbook` | 310 | Kapitelstruktur |
| ✅ Audits | `/qm/audits` | 320 | Audit-Management |
| 🧹 Hygiene | `/qm/hygiene` | 330 | Hygieneprotokolle |
| ✅ Compliance | `/qm/compliance` | 340 | Compliance-Checks |

### Beziehung zum standalone KI-QM Projekt

**KI-QM** (`C:\QM\` bzw. `projects/ki-qm/`) ist das eigenständige Vorgängerprojekt:
- Standalone-App mit eigenem Frontend (React), eigenem Backend (FastAPI), eigener KI (GPT4All/Mistral 7B)
- Komplett offline-fähig, als EXE bündelbar
- Umfangreichere Fachlogik: 31 BLZK-Module, QM Doctor (Vollständigkeitsprüfung), AI Teacher (Trainingsdaten), RAG mit FAISS
- Eigenes Revisions-System, Telegram-Bot-Interface

**VERA QM ist die integrierte Version:**
- Nutzt die BLZK-Struktur und Fachkonzepte aus KI-QM
- Vereinfacht: 5 Kernbereiche (Documents, Handbook, Audits, Hygiene, Compliance)
- Teilt sich VERA-Infrastruktur (Auth, Dokumente, UI, Lizenz)
- Standalone-Funktionalität von KI-QM bleibt als Fallback erhalten

**Migration:** QM-Datenmodelle (`models.py`) sind von KI-QM's `qm_structure.py` und `db/models.py` abgeleitet. Enums (QMMainArea, QMGrundelement, DocumentStatus, QuestionType) stimmen überein.

### Bekannte Fallen / Offene Issues

1. **In-Memory Store!** Alle Daten (Dokumente, Audits, Hygiene, Compliance) werden in Listen/Dicts gehalten. Neustart = Datenverlust. TODO: SQLAlchemy-Persistenz.
2. **Handbuch statisch geseedet:** Die 13 Kapitel sind hardcodiert im Router. Sollte aus `config/qm_structure.yaml` kommen.
3. **Audit-Fragen fest verdrahtet:** 10 Default-Fragen im Router. KI-QM hat dynamische Fragengenerierung (qm_questions.py) — noch nicht integriert.
4. **Keine KI-Integration:** VERA QM hat (noch) keine LLM-gestützte Dokumentengenerierung oder Audit-Auswertung. KI-QM hat das.
5. **Versionierung simpel:** Minor-Bump bei Content-Änderung. Kein semantisches Diffing wie in KI-QM's `revision_manager.py`.
6. **Kein QM Doctor:** Die Vollständigkeitsprüfung aus KI-QM (`doctor/qm_doctor.py`) fehlt noch.

---

## I. Sub-Agent Zuständigkeiten

### Architektur-Überblick

VERA Office ist EIN Produkt mit mehreren Modulen. Jeder Sub-Agent liest das **GESAMTE BRAIN.md**, arbeitet aber **NUR in seinem Bereich**.

```
┌─────────────────────────────────────────────────┐
│                VERA Office (BRAIN.md)            │
├─────────────┬──────────────┬──────────┬─────────┤
│  docagent   │  vera-core   │ vera-erp │ vera-qm │
│  (Basis)    │  (Kern)      │ (Modul)  │ (Modul) │
└─────────────┴──────────────┴──────────┴─────────┘
```

### Sub-Agent Abgrenzung

| Sub-Agent | Zuständigkeit | Dateien |
|-----------|--------------|---------|
| **docagent** | VERA Basis: OCR, Klassifikation, Ablage, Suche, Chat, Onboarding | `backend/core/`, `backend/api/`, `frontend/src/views/` (Basis-Views) |
| **vera-core** | Lizenz- & Modulsystem: Plugin-Registry, Middleware, Frontend-Guards | `backend/modules/base.py`, `registry.py`, `license.py`, `ModuleLock.vue`, `LicenseInput.vue` |
| **vera-erp** | ERP-Modul: Finanzen, Dashboard, Reports, DATEV | `backend/modules/erp/`, `frontend/src/views/ERP/` |
| **vera-qm** | QM-Modul: Dokumente, Handbuch, Audits, Hygiene, Compliance | `backend/modules/qm/`, `frontend/src/views/QM/` |

### Regeln

1. **Jeder Sub-Agent liest BRAIN.md komplett** — Gesamtverständnis ist Pflicht
2. **Jeder Sub-Agent arbeitet NUR in seinem Bereich** — keine Cross-Modul-Änderungen
3. **Abhängigkeiten kommunizieren:** Wenn vera-erp eine Änderung in vera-core braucht → Javix koordiniert
4. **BRAIN.md updaten:** Wenn sich Architektur/Verhalten im eigenen Bereich ändert → Abschnitt aktualisieren
5. **Kein Code in fremden Modulen anfassen** — auch nicht "nur ein kleiner Fix"

### Abhängigkeitskette

```
docagent (Basis) ← vera-core (Modulsystem) ← vera-erp (nutzt Registry + Dokumente)
                                            ← vera-qm  (nutzt Registry + Dokumente)
```

- **vera-erp** und **vera-qm** sind voneinander UNABHÄNGIG
- Beide hängen von **vera-core** (Modulsystem) und **docagent** (Basisdokumente) ab
- Änderungen in vera-core betreffen potentiell ALLE Module → Javix muss koordinieren

---

---

## J. Frontend-Architektur (QM + ERP Module)

> Hinzugefügt: 2026-02-23 — Dokumentation der vom Frontend-Agent erstellten Views

### Überblick

Das Frontend nutzt **Vue 3 + TypeScript + Quasar + Pinia + Vite**. Die QM- und ERP-Module folgen einem einheitlichen Pattern:

```
View (*.vue) → Store (Pinia) → API-Service (Axios) → Backend (/api/modules/{modul}/...)
```

### Dateistruktur

```
frontend/src/
├── services/
│   ├── api.ts              # Basis Axios-Instanz (alle Module nutzen diese)
│   ├── qm-api.ts           # QM API-Wrapper (alle /modules/qm/* Endpoints)
│   └── erp-api.ts          # ERP API-Wrapper (alle /modules/erp/* Endpoints)
├── stores/
│   ├── qm.ts               # QM Pinia Store (Dashboard, Documents, Audits, Hygiene, Compliance, Handbook)
│   └── erp.ts              # ERP Pinia Store (Items, Dashboard, BWA, USt, OpenItems, Stats)
├── views/
│   ├── qm/
│   │   ├── QmDashboardView.vue    # /qm
│   │   ├── QmHandbookView.vue     # /qm/handbook
│   │   ├── QmAuditsView.vue       # /qm/audits
│   │   ├── QmHygieneView.vue      # /qm/hygiene
│   │   └── QmComplianceView.vue   # /qm/compliance
│   └── erp/
│       ├── ErpDashboardView.vue   # /finanzen
│       ├── ErpBwaView.vue         # /finanzen/bwa
│       ├── ErpUstView.vue         # /finanzen/ust
│       ├── ErpOpenItemsView.vue   # /finanzen/offene-posten
│       └── ErpDatevExportView.vue # /finanzen/datev
├── router/
│   └── index.ts            # Alle Routes inkl. QM + ERP
└── App.vue                 # Layout mit Sidebar (Lizenz-Gating für Module)
```

### Router-Struktur (Pfad → View → Name)

**QM-Routen:**
| Pfad | View | Name | Requiresonboarding |
|------|------|------|----|
| `/qm` | `QmDashboardView.vue` | QmDashboard | ✅ |
| `/qm/handbook` | `QmHandbookView.vue` | QmHandbook | ✅ |
| `/qm/audits` | `QmAuditsView.vue` | QmAudits | ✅ |
| `/qm/hygiene` | `QmHygieneView.vue` | QmHygiene | ✅ |
| `/qm/compliance` | `QmComplianceView.vue` | QmCompliance | ✅ |

**ERP-Routen:**
| Pfad | View | Name | Requiresonboarding |
|------|------|------|----|
| `/finanzen` | `ErpDashboardView.vue` | ErpDashboard | ✅ |
| `/finanzen/bwa` | `ErpBwaView.vue` | ErpBwa | ✅ |
| `/finanzen/ust` | `ErpUstView.vue` | ErpUst | ✅ |
| `/finanzen/offene-posten` | `ErpOpenItemsView.vue` | ErpOpenItems | ✅ |
| `/finanzen/datev` | `ErpDatevExportView.vue` | ErpDatev | ✅ |

**⚠️ ERP-Pfade heißen `/finanzen/*`** (deutsche URLs), nicht `/erp/*`!

### Sidebar-Struktur (App.vue)

Die Sidebar hat 4 Sektionen, dynamisch per Lizenz-Gating:

```
┌─ VERA (Header) ──────────────────────┐
│                                       │
│ 📦 Kern (immer sichtbar)             │
│   ├── VERA Chat        → /           │
│   ├── Dashboard         → /dashboard │
│   ├── Dokumente         → /documents │
│   ├── Erfassung         → /capture   │
│   ├── Suche             → /search    │
│   └── Aufgaben          → /tasks     │
│                                       │
│ 📋 Qualitätsmanagement (wenn qmEnabled) │
│   ├── QM Dashboard      → /qm           │
│   ├── QM Handbuch       → /qm/handbook   │
│   ├── Audits            → /qm/audits     │
│   ├── Hygiene           → /qm/hygiene    │
│   └── Compliance        → /qm/compliance │
│                                       │
│ 📊 Finanzen (wenn erpEnabled)        │
│   ├── Finanzen           → /finanzen            │
│   ├── BWA                → /finanzen/bwa        │
│   ├── USt-Voranmeldung   → /finanzen/ust        │
│   ├── Offene Posten      → /finanzen/offene-posten │
│   └── DATEV-Export       → /finanzen/datev      │
│                                       │
│ ⚙️ Einstellungen                     │
│   └── Einstellungen     → /settings  │
└───────────────────────────────────────┘
```

**Lizenz-Gating:** `App.vue` ruft `GET /api/modules/status` auf. Wenn ein Modul `active !== false` → sichtbar. Default: alle sichtbar (graceful degradation bei API-Fehler).

### View → Store → API-Service Mapping

#### QM-Modul

| View | Store-Methoden | API-Endpoints |
|------|---------------|---------------|
| **QmDashboardView** | `fetchDashboard()` | `GET /modules/qm/dashboard` |
| **QmHandbookView** | `fetchHandbook()`, `createDocument()` | `GET /modules/qm/handbook`, `GET /modules/qm/handbook/{id}`, `POST /modules/qm/documents` |
| **QmAuditsView** | `fetchAudits()`, `fetchAudit()`, `createAudit()`, `answerQuestion()`, `finalizeAudit()`, `deleteAudit()` | `GET/POST /modules/qm/audits`, `GET/DELETE /modules/qm/audits/{id}`, `PUT /modules/qm/audits/{id}/answer/{qid}`, `POST /modules/qm/audits/{id}/finalize` |
| **QmHygieneView** | `fetchHygiene()`, `fetchHygieneDetail()`, `createHygiene()`, `checkHygieneItem()`, `deleteHygiene()` | `GET/POST /modules/qm/hygiene`, `GET /modules/qm/hygiene/{id}`, `PUT /modules/qm/hygiene/{id}/check` |
| **QmComplianceView** | `fetchCompliance()`, `createCompliance()`, `updateCompliance()`, `deleteCompliance()` | `GET/POST/PATCH/DELETE /modules/qm/compliance` |

#### ERP-Modul

| View | Store-Methoden | API-Endpoints |
|------|---------------|---------------|
| **ErpDashboardView** | `fetchDashboard(start, end)` | `GET /modules/erp/dashboard?start=&end=` |
| **ErpBwaView** | `fetchBWA(start, end)` | `GET /modules/erp/reports/bwa?start=&end=` |
| **ErpUstView** | `fetchUSt(start, end)` | `GET /modules/erp/reports/ust?start=&end=` |
| **ErpOpenItemsView** | `fetchOpenItems(direction?)`, `updateItem()` | `GET /modules/erp/open-items`, `PATCH /modules/erp/items/{id}` |
| **ErpDatevExportView** | *(direkt via erpApi)* | `GET /modules/erp/reports/datev`, `GET /modules/erp/reports/csv` |

### Ampel-System

Wird an zwei Stellen eingesetzt:

**1. QM Compliance-Ampel** (QmDashboardView):
- 🟢 `compliance_rate >= 80%` → "✅ Konform" (grüner Kreis leuchtet)
- 🟡 `compliance_rate 50–79%` → "⚠️ Teilweise" (gelber Kreis leuchtet)
- 🔴 `compliance_rate < 50%` → "🔴 Kritisch" (roter Kreis leuchtet)
- Darstellung: 3 große `q-icon name="circle"` nebeneinander, nur der aktive ist farbig, Rest grau

**2. ERP Offene Posten** (ErpOpenItemsView):
- 🟢 `status_color === 'green'` → OK (>7 Tage bis Fälligkeit)
- 🟡 `status_color === 'yellow'` → Bald fällig (≤7 Tage)
- 🔴 `status_color === 'red'` → Überfällig
- `status_color` kommt vom Backend (berechnet anhand `due_date` vs. heute)

**3. QM Compliance per Kategorie** (QmComplianceView):
- Jede der 6 G-BA Grundelement-Kategorien hat eine `q-linear-progress`-Bar
- Farbe: grün ≥80%, amber ≥50%, rot <50%

### Dialog-Patterns

**CRUD-Dialoge (Create/Edit in `q-dialog`):**

| View | Create-Dialog | Detail/Edit-Dialog | Delete-Confirm |
|------|--------------|-------------------|----------------|
| QmAuditsView | ✅ (Titel + Auditor) | ✅ Maximized (Fragenkatalog, Findings, Finalize) | ✅ `$q.dialog()` |
| QmHandbookView | ✅ (Dokument mit Titel, Bereich, Inhalt) | ✅ Maximized (Kapitel-Detail + verknüpfte Docs) | — |
| QmHygieneView | ✅ (Titel + Bereich) | ✅ Maximized (Checklist mit Checkboxen) | ✅ `$q.dialog()` |
| QmComplianceView | ✅ (Titel, Kategorie, Anforderung, Fällig) | ✅ (gleicher Dialog im Edit-Modus) | ✅ `$q.dialog()` |
| ErpOpenItemsView | — | — (nur "Als bezahlt markieren" Button) | — |
| ErpDatevExportView | — | — (Parameter-Eingabe inline) | — |
| ErpDashboardView | — | — (reine Anzeige) | — |
| ErpBwaView | — | — (reine Anzeige) | — |
| ErpUstView | — | — (reine Anzeige) | — |

**Pattern:** Maximized Dialoge (`maximized transition-show="slide-up"`) für komplexe Detail-Ansichten (Audits, Hygiene, Handbuch-Kapitel). Normale Dialoge für einfache Formulare.

### Quasar-Components Übersicht

| Component | Wo genutzt | Zweck |
|-----------|-----------|-------|
| `q-layout` / `q-drawer` | App.vue | Haupt-Layout mit Sidebar |
| `q-table` | Audits, Hygiene, Compliance, BWA, OpenItems | Datentabellen mit Sortierung |
| `q-card` | Alle Views | KPI-Karten, Inhaltscontainer |
| `q-dialog` | Audits, Hygiene, Compliance, Handbook | CRUD-Dialoge (create/detail) |
| `q-badge` | Überall | Status-Labels, Ampel-Farben |
| `q-linear-progress` | Audits (Fortschritt), Hygiene (Checklist), Compliance (Rate), ERP Dashboard (Monatschart) |
| `q-skeleton` | Dashboard-Views | Loading-States |
| `q-checkbox` | Hygiene-Detail | Checklist-Items abhaken |
| `q-select` | Compliance (Filter), Handbook (Bereich) | Dropdowns |
| `q-chip` | Audits (Auditor), OpenItems (Richtung) | Kompakte Labels |
| `q-notify` (via `Notify.create`) | Alle mit CRUD | Erfolgs-/Fehlermeldungen |
| `$q.dialog()` | Audits, Hygiene, Compliance | Lösch-Bestätigungen |

### Store-Pattern

Beide Stores (qm.ts, erp.ts) folgen dem gleichen Pattern:
- **Composition API** (`defineStore` mit Setup-Funktion)
- **`ref()` für State**, keine reactive Objects
- **`loading` ref** pro Store (global, nicht pro Action)
- **fetch-Methoden** setzen `loading=true`, wrappen in try/finally
- **create/update** rufen nach Erfolg automatisch die Liste neu ab (`fetchItems()` / `fetchDocuments()`)
- **Keine Typisierung** — alles `any` (TypeScript-Interfaces fehlen noch)

### API-Service-Pattern

Beide Services (qm-api.ts, erp-api.ts):
- Importieren `api` aus `./api` (zentrale Axios-Instanz)
- Exportieren ein Objekt mit async-Methoden
- Jede Methode = 1 API-Call, returned `response.data`
- **Download-Pattern** (nur erp-api): `responseType: 'blob'` → `URL.createObjectURL` → unsichtbarer Link-Click → Cleanup

---

## LERNPROTOKOLL

### 2026-02-23 — Frontend QM + ERP Views dokumentiert

**Was wurde gemacht:**
Ein Frontend-Agent hat 20 Dateien erstellt (5 QM Views, 5 ERP Views, 2 Stores, 2 API-Services, Router-Update, App.vue-Update) — ohne jegliche Dokumentation in BRAIN.md.

**Architektur-Entscheidungen die getroffen wurden:**
1. **Deutsche URLs für ERP:** `/finanzen/*` statt `/erp/*` — benutzerfreundlicher für deutsche KMU
2. **QM URLs englisch-deutsch mix:** `/qm/*` (kurz genug)
3. **Sidebar-Gating via API-Call:** `GET /api/modules/status` — Module defaulten auf sichtbar bei Fehler (graceful degradation)

[Showing lines 1-1112 of 1412 (50.0KB limit). Use offset=1113 to continue.]