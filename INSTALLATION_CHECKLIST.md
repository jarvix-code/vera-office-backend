# VERA Office - AI Installation Checklist

**Datum:** 2026-02-21  
**Status:** Code komplett, Dependencies teilweise installiert

---

## Status Check

Fuehre zuerst das Test-Script aus:

```bash
cd C:\Jarvix\vera-office
$env:PYTHONPATH="C:\Jarvix\vera-office"
python test_ai_setup.py
```

Das zeigt dir genau was noch fehlt.

---

## Installations-Schritte

### 1. Dependencies installieren (ERLEDIGT)

```bash
pip install -r requirements.txt
```

**Status:**
- [x] fastapi, uvicorn
- [x] sqlalchemy
- [x] opencv, pillow, numpy
- [x] pytesseract, reportlab
- [x] pyyaml, loguru
- [x] scikit-learn (fuer TF-IDF)
- [x] zeroconf (fuer mDNS)
- [ ] llama-cpp-python (FEHLT - siehe unten)

---

### 2. llama-cpp-python installieren (MANUELL)

**Problem:** Braucht C++ Compiler

**Loesung A - Visual Studio Build Tools (empfohlen):**

1. Download: https://visualstudio.microsoft.com/downloads/
2. Installiere "Desktop Development with C++"
3. Nach Installation:
   ```bash
   pip install llama-cpp-python
   ```

**Loesung B - Pre-built Wheel (wenn verfuegbar):**

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

**Loesung C - Ohne LLM betreiben:**
- VERA laeuft auch ohne LLM
- Manuelle Kategorisierung statt automatisch
- Alle anderen Features funktionieren

---

### 3. Model Download (MANUELL - 4.4 GB!)

**Via Browser (empfohlen):**

1. Oeffne: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-GGUF
2. Klicke auf "Files and versions"
3. Download: `mistral-7b-instruct-v0.3.Q4_K_M.gguf` (4.37 GB)
4. Verschiebe nach: `C:\Jarvix\vera-office\models\`

**Verify:**
```bash
dir C:\Jarvix\vera-office\models\
# Sollte ~4.4 GB Datei zeigen
```

---

### 4. Test AI Setup

```bash
python test_ai_setup.py
```

**Erwartetes Ergebnis:**
```
[OK] All AI modules imported successfully
[OK] LLM available (llama-cpp-python + model loaded)
[OK] Model found: mistral-7b-instruct-v0.3.Q4_K_M.gguf (4.37 GB)
[OK] AI config found in vera.yaml
[OK] FULLY READY - All AI features available
```

---

### 5. Backend starten

```bash
cd C:\Jarvix\vera-office
$env:PYTHONPATH="C:\Jarvix\vera-office"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Erwartete Logs:**
```
VERA Office Backend startet...
LLM model loaded successfully
mDNS service registered: vera-office.local:8000
VERA Office Backend bereit auf 0.0.0.0:8000
```

---

### 6. API testen

**Browser:**
- http://localhost:8000/api/docs (Swagger UI)
- http://localhost:8000/health (Health Check)

**Neue AI-Endpoints:**
- POST /api/documents/{id}/classify
- POST /api/documents/{id}/feedback
- GET /api/documents/feedback/stats

**Test via curl:**
```bash
# Health Check
curl http://localhost:8000/health

# Feedback Stats (sollte leer sein)
curl http://localhost:8000/api/documents/feedback/stats
```

---

### 7. mDNS testen (von anderem Geraet)

**macOS/Linux:**
```bash
dns-sd -B _http._tcp
# Sollte "vera-office" finden
```

**Windows:**
```powershell
Resolve-DnsName vera-office.local
# Sollte IP-Adresse zurueckgeben
```

**Browser:**
- http://vera-office.local:8000/

---

## Troubleshooting

### LLM laed nicht

**Check 1: llama-cpp-python installiert?**
```bash
pip list | findstr llama
# Sollte: llama-cpp-python==...
```

**Check 2: Model vorhanden?**
```bash
dir C:\Jarvix\vera-office\models\
# Sollte 4.4 GB Datei zeigen
```

**Check 3: Config korrekt?**
```bash
type C:\Jarvix\vera-office\config\vera.yaml
# Sollte ai: section haben
```

### mDNS nicht sichtbar

- Windows Firewall: Port 5353 UDP erlauben
- Netzwerk: .local muss erlaubt sein
- Corporate Networks blocken oft mDNS

### Klassifikation immer "unknown"

- Kategorien erstellt? (Onboarding Step 2)
- LLM verfuegbar? (Check Logs)
- OCR-Text vorhanden? (Check Document-Details)

---

## Naechste Schritte

Nach erfolgreicher Installation:

1. **Onboarding durchlaufen:**
   - Unternehmensprofil
   - Dokumenttypen erstellen
   - Netzwerk-Config

2. **Test-Dokument hochladen:**
   - Via API: POST /api/documents/upload
   - Hotfolder: Datei in data/inbox/ kopieren

3. **Klassifikation testen:**
   - Check ob automatisch kategorisiert
   - Check Confidence-Score
   - Bei Fehler: Feedback geben

4. **Learning Loop:**
   - User-Korrekturen via /feedback
   - Nach 10+ Korrekturen: Bessere Klassifikation
   - Stats checken: /api/documents/feedback/stats

---

## Checkliste (zum Abhaken)

- [ ] requirements.txt installiert
- [ ] llama-cpp-python installiert
- [ ] Mistral 7B Model downloaded (4.4 GB)
- [ ] Model in models/ Ordner
- [ ] test_ai_setup.py laeuft durch
- [ ] Backend startet ohne Fehler
- [ ] API docs erreichbar (localhost:8000/api/docs)
- [ ] mDNS funktioniert (vera-office.local)
- [ ] Onboarding durchlaufen
- [ ] Test-Dokument hochgeladen
- [ ] Klassifikation funktioniert

---

## Hilfe

Bei Problemen siehe:
- **AI_SETUP.md** - Detaillierte LLM-Installation
- **VERA_AI_IMPLEMENTATION_SUMMARY.md** - Technische Details
- **backend/core/ai/README.md** - Module-Dokumentation

Backend-Logs checken fuer detaillierte Fehler:
```
WARN - llama-cpp-python not installed
ERROR - Failed to load LLM model
```

---

**Viel Erfolg! 🚀**
