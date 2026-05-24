# 🚀 VERA Office - Setup-Anleitung

## Voraussetzungen

### 1. Python 3.12+ installieren

**Windows:**
- Download: https://www.python.org/downloads/
- **WICHTIG:** Bei Installation "Add Python to PATH" ankreuzen!
- Version prüfen: `python --version`

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

### 2. Docker (Optional, aber empfohlen)

**Windows:**
- Docker Desktop: https://www.docker.com/products/docker-desktop/

**Linux:**
```bash
sudo apt install docker.io docker-compose
sudo usermod -aG docker $USER  # Logout/Login danach
```

---

## 📦 Installation

### Variante A: Mit Setup-Script (Windows)

```batch
# 1. Setup-Script ausführen
setup.bat

# 2. Server starten
start.bat
```

### Variante B: Manuell

```bash
# 1. Virtual Environment erstellen
python -m venv venv

# 2. Aktivieren (Windows)
venv\Scripts\activate.bat

# 2. Aktivieren (Linux/Mac)
source venv/bin/activate

# 3. Dependencies installieren
pip install -r backend/requirements.txt

# 4. Server starten
python backend/main.py
```

### Variante C: Docker (Empfohlen für Deployment)

```bash
cd docker
docker-compose up -d

# Logs anschauen
docker-compose logs -f backend

# Stoppen
docker-compose down
```

---

## ✅ Testen

### 1. Health-Check

```bash
curl http://localhost:8000/health
```

**Erwartete Antwort:**
```json
{
  "status": "healthy",
  "app": "VERA Office",
  "version": "1.0.0-alpha",
  "hotfolder_enabled": true,
  "database": "ok"
}
```

### 2. API-Dokumentation öffnen

Browser: **http://localhost:8000/docs**

### 3. Testdokument verarbeiten

```bash
# Kopiere ein Bild/PDF in den Inbox-Ordner
copy test_rechnung.jpg data\inbox\

# VERA verarbeitet automatisch und speichert in data/documents/
```

---

## 🔧 Konfiguration

Konfiguration in: **config/vera.yaml**

**Wichtige Einstellungen:**
```yaml
# Hotfolder aktivieren/deaktivieren
hotfolder_enabled: true

# OCR-Sprache
ocr_language: "de"  # Deutsch

# Bildqualität (0-100)
image_quality: 85

# Klassifikations-Schwelle (0.0-1.0)
classification_threshold: 0.8
```

---

## 🐛 Troubleshooting

### "Python not found"

→ Python nicht im PATH. Neu installieren mit "Add to PATH" aktiviert.

### "ModuleNotFoundError: No module named 'paddleocr'"

→ Dependencies nicht installiert:
```bash
pip install -r backend/requirements.txt
```

### PaddleOCR lädt ewig

→ Beim ersten Start werden OCR-Modelle geladen (~100MB). Das dauert beim ersten Mal.

### OpenCV-Fehler (Linux)

```bash
sudo apt-get install libgl1-mesa-glx libglib2.0-0
```

### Port 8000 bereits belegt

→ Anderen Port nutzen:
```bash
# In config/vera.yaml
port: 8001

# Oder Environment Variable
export PORT=8001
python backend/main.py
```

---

## 📊 Entwicklung

### Logs anschauen

```bash
# Docker
docker-compose logs -f backend

# Lokal
tail -f data/logs/vera_*.log  # Linux/Mac
Get-Content data\logs\vera_*.log -Wait  # Windows PowerShell
```

### Datenbank zurücksetzen

```bash
rm data/vera.db
python backend/main.py  # Erstellt neue DB
```

### Tests schreiben (Phase 2)

```bash
pip install pytest pytest-asyncio
pytest tests/
```

---

## 🎯 Nächste Schritte

**Phase 1 ✅ Abgeschlossen:**
- Backend-Grundgerüst
- Hotfolder-Watcher
- Bildverarbeitung
- OCR
- PDF-Generierung
- API

**Phase 2 (TODO):**
- [ ] Classifier (LLM-basiert)
- [ ] Namer (intelligente Dateibenennung)
- [ ] Filer (strukturierte Ablage)
- [ ] Frontend (Vue 3 + iPad)
- [ ] Tests

---

## 📞 Support

Siehe **README.md** und **PROJECT.md** für Details.

**Happy Document Management! 🏢**
