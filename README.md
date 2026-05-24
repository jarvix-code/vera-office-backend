# VERA Office - Dokumenten-Agent

**Stand:** 2026-03-18  
**Location:** `C:\VERA-Office`

---

## 🚀 Schnellstart

### Option 1: Docker (Empfohlen)

**Erstmalige Installation:**
```bash
INSTALL.bat
```

**VERA starten:**
```bash
START.bat
```
Oder: Desktop-Verknüpfung doppelklicken

**VERA stoppen:**
```bash
STOP.bat
```

**Browser:**
- http://localhost:8000

---

### Option 2: Manuell (ohne Docker)

**VERA starten:**
```bash
start-vera-http.bat
```

**Browser:**
- http://localhost:8000

---

## 📁 Struktur

```
C:\VERA-Office\
├── backend/              # FastAPI Backend
├── frontend/dist/        # Vue.js Frontend (gebaut)
├── data/                 # Dokumente & OCR-Ergebnisse
├── logs/                 # Application Logs
├── models/               # KI-Modelle (Mistral)
├── paddleocr-models/     # OCR-Modelle
├── config/               # Konfiguration
├── keys/                 # SSL Certificates
├── python/               # Embedded Python 3.11
│
├── INSTALL.bat           # 🎯 Docker Installation
├── START.bat             # 🎯 VERA starten (Docker)
├── STOP.bat              # 🎯 VERA stoppen (Docker)
│
├── start-vera-http.bat   # Manueller Start (ohne Docker)
├── docker-compose.yml    # Docker Orchestration
└── Dockerfile            # Container Build
```

---

## ✅ Features

- **OCR:** PaddleOCR (Deutsch + Englisch)
- **KI:** Mistral 7B (lokal, optional)
- **Frontend:** Vue 3 + Vite
- **Backend:** FastAPI + Uvicorn
- **Deployment:** Docker oder Standalone

---

## 🔧 Troubleshooting

### Docker läuft nicht
```bash
docker --version
```
Falls nicht installiert: https://www.docker.com/products/docker-desktop

### Logs anzeigen
```bash
docker-compose logs -f
```

### Container neustarten
```bash
STOP.bat
START.bat
```

### Manuelle Installation nutzen
```bash
start-vera-http.bat
```

---

## 📦 Installation auf anderer Maschine

1. **Kompletten Ordner kopieren:**
   - `C:\VERA-Office` → Ziel-PC

2. **Docker installieren** (falls noch nicht vorhanden)

3. **INSTALL.bat ausführen**

4. **START.bat ausführen**

Fertig! 🎉

---

## 🎯 Für Boris

**Doppelklick:**
- Desktop-Verknüpfung "VERA Office" → Startet automatisch
- Browser öffnet sich bei http://localhost:8000

**KEIN Source-Code-Handling nötig!**

---

## 📝 Tech Stack

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **Frontend:** Vue 3, Vite, TypeScript
- **OCR:** PaddleOCR 3.4.0
- **KI:** llama-cpp-python (Mistral 7B)
- **Container:** Docker 29.2.0

---

**Erstellt von:** Javix  
**Datum:** 2026-03-18
