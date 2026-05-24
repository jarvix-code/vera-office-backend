# VERA Sandbox - Ready for Use

**Status:** 🔨 BUILDING (läuft gerade)  
**ETA:** ~5-10 Minuten  
**Build-Session:** grand-lagoon (PID 2284)

---

## ⏳ Was passiert gerade?

Docker baut VERA Sandbox-Container:
1. ✅ Python 3.12 (Debian 12 Bookworm)
2. ✅ System-Dependencies (OpenCV, OCR-Libraries)
3. 🔨 DevOps-Tools (curl, wget, git, vim, nano, htop, jq, tree) **← LÄUFT**
4. ⏳ PowerShell Core (Debian 12 Packages)
5. ⏳ Shell-Aliases (md, cls, ll, ps1)
6. ⏳ Python Dependencies (FastAPI, PaddleOCR, etc.)
7. ⏳ VERA Backend-Code

**Warum so lange?**  
→ PowerShell Core ist ~150 MB + Python Dependencies ~500 MB = erste Build dauert länger

---

## 📋 Nach Build abgeschlossen

### Schritt 1: Container starten

```powershell
cd C:\Jarvix\vera-office
.\start-sandbox.ps1
```

**Was passiert:**
- Docker Desktop startet (falls nicht schon läuft)
- VERA Container startet
- Health Check läuft (wartet bis Backend bereit)
- Status wird angezeigt

**Erwartete Ausgabe:**
```
=====================================
  VERA Sandbox ist bereit!
=====================================

Nächste Schritte:
  1. Sandbox betreten:  docker exec -it vera-backend bash
  2. PowerShell:        pwsh
  3. VERA testen:       curl http://localhost:8000/health
```

---

### Schritt 2: In Sandbox einsteigen

```powershell
docker exec -it vera-backend bash
```

**Du bist jetzt IN der Sandbox** (Linux-Container):
```
root@vera-backend:/app#
```

---

### Schritt 3: Testen

```bash
# PowerShell starten
pwsh

# Windows-Befehle testen
md test          # → mkdir -p test (funktioniert!)
cls              # → clear (funktioniert!)
ll               # → ls -lah (funktioniert!)
ps1              # → pwsh (funktioniert!)

# VERA testen
curl http://localhost:8000/health
# Erwartung: {"status":"healthy","version":"1.0.0-alpha"}

# Tools testen
which curl wget git vim nano htop jq tree
# Erwartung: Alle gefunden

# Python/OCR testen
python -c "import paddleocr; print('PaddleOCR OK')"
# Erwartung: PaddleOCR OK
```

---

## 🎯 Was kannst du jetzt machen?

### Typische Use-Cases

#### 1️⃣ **VERA Backend testen (ohne Windows zu riskieren)**

```bash
# In Sandbox
cd /app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Backend läuft jetzt in Sandbox
# Von Windows aus testen:
curl http://localhost:8000/health
```

#### 2️⃣ **Code-Änderungen sicher testen**

```bash
# In Sandbox
nano /app/backend/main.py
# Änderung machen, speichern

# Backend neu starten
pkill -f uvicorn
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Testen - wenn OK: committen
# Wenn kaputt: Container neu starten = Änderungen weg
```

#### 3️⃣ **Debugging mit voller Linux-Toolchain**

```bash
# Logs anschauen
tail -f /app/logs/backend.log

# Prozesse monitoren
htop

# Datenbank inspizieren
sqlite3 /app/data/vera.db

# API-Calls debuggen
curl -v http://localhost:8000/api/documents/list | jq .
```

#### 4️⃣ **PowerShell-Skripte in Linux laufen lassen**

```bash
pwsh

# Du bist jetzt in PowerShell (auf Linux!)
Get-ChildItem /app
Get-Process | Where-Object { $_.Name -like "python*" }
```

---

## 🔄 Sandbox-Lifecycle

### Starten
```powershell
.\start-sandbox.ps1
```

### Stoppen
```powershell
docker-compose -f docker\docker-compose.yml down
```

### Neu starten (schnell, behält Daten)
```powershell
docker restart vera-backend
```

### Zurücksetzen (ACHTUNG: Daten weg!)
```powershell
docker-compose -f docker\docker-compose.yml down -v
.\start-sandbox.ps1
```

---

## 📁 Persistente Daten

### Was bleibt nach Container-Neustart?

✅ **PERSISTENT:**
- `/app/data/` (Datenbank, Dokumente)
- `/app/config/` (Konfiguration)
- `/app/logs/` (Logs)

❌ **NICHT PERSISTENT:**
- `/app/backend/` Code-Änderungen
- Installierte Packages (außer in requirements.txt)
- Shell-Historie
- `/root/` Home-Verzeichnis

**Tipp:** Code-Änderungen committen oder nach `/app/data/` kopieren!

---

## 📚 Dokumentation

### Vollständige Guides
- **SANDBOX_GUIDE.md** - Komplette Anleitung (Befehle, Debugging, Troubleshooting)
- **start-sandbox.ps1** - One-Click-Starter
- **docker-compose.yml** - Container-Konfiguration

### Wichtigste Befehle (Cheatsheet)
```bash
# Rein/Raus
docker exec -it vera-backend bash    # Reingehen
exit                                  # Rausgehen

# PowerShell
pwsh                                  # Starten
exit                                  # Beenden

# Dateisystem
md test                               # Ordner erstellen
cls                                   # Terminal leeren
ll                                    # Dateien anzeigen
tree /app                             # Struktur

# VERA
curl http://localhost:8000/health     # Health Check
tail -f /app/logs/backend.log         # Logs live

# Datenbank
sqlite3 /app/data/vera.db             # DB öffnen

# Tools
htop                                  # Prozesse
df -h                                 # Speicher
git status                            # Git
```

---

## 🐛 Troubleshooting

### "Container läuft nicht"
```powershell
docker ps -a | findstr vera
docker logs vera-backend --tail 50
```

### "Kann nicht einsteigen"
```powershell
# Container läuft?
docker ps | findstr vera

# Falls nicht
docker-compose -f docker\docker-compose.yml up -d
```

### "PowerShell fehlt"
```bash
# In Sandbox
which pwsh

# Falls nicht vorhanden
# → Image neu bauen (Build läuft gerade!)
```

### "Backend startet nicht"
```bash
# Logs prüfen
tail -n 100 /app/logs/backend.log

# Dependencies prüfen
pip list | grep paddle
pip list | grep opencv

# Falls fehlen
pip install paddleocr paddlepaddle opencv-python
```

---

## ✅ Checkliste nach Build

Wenn Build fertig ist (in ~5-10 Min), teste:

- [ ] Container läuft: `docker ps | findstr vera`
- [ ] Health Check OK: `curl http://localhost:8000/health`
- [ ] Kann einsteigen: `docker exec -it vera-backend bash`
- [ ] PowerShell verfügbar: `pwsh --version`
- [ ] Aliases funktionieren: `md`, `cls`, `ll`, `ps1`
- [ ] Tools verfügbar: `curl`, `wget`, `git`, `vim`, `htop`, `jq`, `tree`
- [ ] OCR importierbar: `python -c "import paddleocr"`

**Wenn ALLE ✓ → Sandbox ist production-ready! 🎉**

---

## 🎁 Bonus: Multi-Terminal Setup

**Optimal Workflow für Debugging:**

**Terminal 1 (Sandbox-Shell):**
```powershell
docker exec -it vera-backend bash
pwsh
```

**Terminal 2 (Logs live):**
```powershell
docker logs -f vera-backend
```

**Terminal 3 (API-Tests von Windows):**
```powershell
curl http://localhost:8000/health
curl http://localhost:8000/api/documents/list | jq .
```

---

## 📞 Build-Status prüfen

Während Build läuft, kannst du Live-Output sehen:

```powershell
# Session-Status
docker ps -a

# Build-Logs (wenn noch im Hintergrund)
# (wird in 5-10 Min automatisch fertig)
```

---

**Build läuft - Geduld! ☕**  
**Sobald fertig, melde ich mich!**

*Javix | 2026-03-07 08:25*
