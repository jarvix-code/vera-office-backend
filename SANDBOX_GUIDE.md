# VERA Office - Sandbox Guide

**Für:** Boris (Testing), Entwickler (Debugging)  
**Zweck:** Sichere Sandbox-Umgebung zum Testen von VERA ohne Windows zu zerstören  
**Status:** ✅ Production-Ready

---

## 🎯 Was ist die Sandbox?

Die VERA Sandbox ist ein **Docker-Container** mit:
- ✅ **Komplettes VERA Backend** (FastAPI, OCR, AI)
- ✅ **PowerShell Core** (Windows-Befehle wie `md`, `cls` funktionieren)
- ✅ **DevOps-Tools** (curl, wget, git, vim, htop, jq, tree)
- ✅ **Linux-Umgebung** (Debian 13 Trixie)
- ✅ **Persistente Daten** (`data/` Ordner bleibt nach Neustart)

**Vorteil:**
- 🔒 Sicher (kein Risiko für Windows)
- ⚡ Schnell (Container startet in Sekunden)
- 🧹 Sauber (löschen = 1 Befehl)
- 🔄 Reproduzierbar (immer gleiche Umgebung)

---

## 🚀 Schnellstart (3 Befehle)

```powershell
# 1. Sandbox starten
cd C:\Jarvix\vera-office
.\start-sandbox.ps1

# 2. In Sandbox einsteigen
docker exec -it vera-backend bash

# 3. Fertig! Du bist jetzt in der Sandbox
# Teste z.B.:
pwsh              # PowerShell Core starten
md test           # Ordner erstellen (mkdir)
cls               # Terminal leeren (clear)
ll                # Dateien anzeigen (ls -lah)
```

---

## 📋 Sandbox-Befehle (Cheatsheet)

### Rein/Raus
```bash
# Sandbox betreten
docker exec -it vera-backend bash

# PowerShell starten (in Sandbox)
pwsh

# Sandbox verlassen
exit    # (oder Ctrl+D)
```

---

### Dateisystem
```bash
md test             # Ordner erstellen (mkdir -p)
cls                 # Terminal leeren (clear)
ll                  # Dateien anzeigen (ls -lah)
tree /app           # Struktur anzeigen

# VERA-Dateien
cd /app/backend     # Backend-Code
cd /app/data        # Datenbank & Dokumente (PERSISTENT!)
cd /app/config      # Konfiguration
cd /app/logs        # Logs
```

---

### VERA Backend testen
```bash
# Health Check
curl http://localhost:8000/health

# Dokumente abrufen
curl http://localhost:8000/api/documents/list

# Kategorien anzeigen
curl http://localhost:8000/api/folders/categories | jq .

# Backend-Logs anschauen
tail -f /app/logs/backend.log

# OCR-Test
python -c "from backend.core.ocr_engine import OCREngine; print(OCREngine())"
```

---

### Datenbank
```bash
# SQLite DB öffnen
sqlite3 /app/data/vera.db

# Dokumente anzeigen
sqlite3 /app/data/vera.db "SELECT id, filename, category_id FROM documents LIMIT 5;"

# Kategorien anzeigen
sqlite3 /app/data/vera.db "SELECT * FROM categories;"
```

---

### Prozesse & System
```bash
htop                # Prozess-Monitor (q zum Beenden)
ps aux              # Prozess-Liste
df -h               # Speicherplatz
du -sh *            # Ordnergröße
```

---

### Code editieren
```bash
# Vim (für Profis)
vim /app/backend/main.py

# Nano (einfacher)
nano /app/config/vera.yaml

# Datei anzeigen
cat /app/backend/main.py | less
```

---

### Git
```bash
git status
git log --oneline
git diff
git add .
git commit -m "Fix: XYZ"
```

---

## 🛠️ VERA Backend starten/stoppen

### Backend manuell starten (in Sandbox)
```bash
cd /app
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Backend stoppen
```bash
# Ctrl+C (wenn im Vordergrund)
# Oder:
pkill -f uvicorn
```

### Backend-Status prüfen
```bash
curl http://localhost:8000/health
# Erwartung: {"status": "healthy", "version": "1.0.0-alpha"}
```

---

## 📦 Dateien zwischen Host & Sandbox kopieren

### Host → Sandbox
```powershell
# Auf Windows (außerhalb Sandbox)
docker cp C:\Temp\test.pdf vera-backend:/app/data/inbox/

# Erwartung: Datei landet in Sandbox unter /app/data/inbox/
```

### Sandbox → Host
```powershell
# Datenbank sichern
docker cp vera-backend:/app/data/vera.db C:\Temp\backup.db

# Logs exportieren
docker cp vera-backend:/app/logs C:\Temp\vera-logs
```

---

## 🐛 Debugging in der Sandbox

### Logs anschauen
```bash
# Backend-Log (live)
tail -f /app/logs/backend.log

# Letzte 50 Zeilen
tail -n 50 /app/logs/backend.log

# Fehler suchen
grep -i error /app/logs/backend.log
```

### Python-Fehler debuggen
```bash
# Python REPL starten
python

# Import testen
>>> from backend.core.ocr_engine import OCREngine
>>> ocr = OCREngine()
>>> print("OCR OK")

# Dependencies prüfen
pip list | grep paddle
pip list | grep opencv
```

### Datenbank-Probleme
```bash
# Schema anzeigen
sqlite3 /app/data/vera.db ".schema"

# Tabellen auflisten
sqlite3 /app/data/vera.db ".tables"

# Dokumente zählen
sqlite3 /app/data/vera.db "SELECT COUNT(*) FROM documents;"
```

---

## 🔄 Sandbox verwalten

### Sandbox starten
```powershell
cd C:\Jarvix\vera-office\docker
docker-compose up -d
```

### Sandbox stoppen
```powershell
docker-compose down
```

### Sandbox neu starten (schnell)
```powershell
docker restart vera-backend
```

### Sandbox komplett löschen (ACHTUNG: Daten weg!)
```powershell
docker-compose down -v  # -v löscht auch Volumes (Datenbank!)
```

### Sandbox Logs anschauen (außerhalb Container)
```powershell
docker logs -f vera-backend
docker logs vera-backend --tail 100
```

---

## 💡 Pro-Tipps

### 1. PowerShell in Sandbox nutzen
```bash
# Bash → PowerShell wechseln
pwsh

# PowerShell One-Liner ausführen (von Bash)
pwsh -NoProfile -Command "Get-ChildItem /app | Format-Table"
```

### 2. Mehrere Terminal-Fenster gleichzeitig
```powershell
# Terminal 1: Backend-Logs (live)
docker logs -f vera-backend

# Terminal 2: Sandbox-Shell (interaktiv)
docker exec -it vera-backend bash

# Terminal 3: API-Requests (von Windows)
curl http://localhost:8000/api/health
```

### 3. VERA komplett zurücksetzen
```powershell
# 1. Container stoppen + löschen
docker-compose down -v

# 2. Neu bauen + starten
docker-compose up -d --build

# 3. Datenbank wird neu erstellt (leer)
```

### 4. Dependencies nachladen (wenn fehlen)
```bash
# In Sandbox
pip install paddleocr paddlepaddle opencv-python
```

### 5. Konfiguration ändern
```bash
# In Sandbox
nano /app/config/vera.yaml

# Danach Container neu starten (damit Änderungen wirksam werden)
# (außerhalb Sandbox:)
docker restart vera-backend
```

---

## 🆘 Troubleshooting

### Problem: "Container startet nicht"
```powershell
# Logs anschauen
docker logs vera-backend --tail 50

# Fehler: "ModuleNotFoundError"
# → Dependencies fehlen → pip install in Sandbox

# Fehler: "Port 8000 already in use"
# → Anderer Prozess nutzt Port 8000
netstat -ano | findstr :8000
# → Prozess beenden oder anderen Port nutzen
```

### Problem: "Kann nicht in Sandbox einsteigen"
```powershell
# Container läuft?
docker ps | findstr vera

# Falls nicht → starten
docker-compose up -d

# Dann nochmal versuchen
docker exec -it vera-backend bash
```

### Problem: "PowerShell nicht gefunden"
```bash
# In Sandbox
which pwsh

# Falls nicht vorhanden → Image neu bauen
# (außerhalb Sandbox:)
docker-compose down
docker-compose up -d --build
```

### Problem: "Datenbank korrupt"
```bash
# Datenbank sichern (außerhalb Sandbox)
docker cp vera-backend:/app/data/vera.db C:\Temp\backup.db

# Datenbank löschen (in Sandbox)
rm /app/data/vera.db

# VERA neu starten → erstellt neue DB
docker restart vera-backend
```

---

## 📊 Was ist persistent? Was nicht?

### ✅ PERSISTENT (bleibt nach Container-Neustart):
- `/app/data/` (Datenbank, Dokumente)
- `/app/config/` (Konfiguration)
- `/app/logs/` (Logs)

**Grund:** Diese Ordner sind als Docker Volumes gemountet

### ❌ NICHT PERSISTENT (geht verloren bei Neustart):
- `/app/backend/` Code-Änderungen (außer du committest sie)
- `/root/` Home-Verzeichnis
- Installierte Packages (außer in requirements.txt)
- Shell-Historie

**Tipp:** Code-Änderungen IMMER committen oder nach `/app/data/` kopieren!

---

## 🎓 Lernressourcen

### Docker-Basics
```bash
docker ps          # Laufende Container
docker ps -a       # Alle Container
docker images      # Alle Images
docker logs <id>   # Container-Logs
docker exec <id>   # In Container einsteigen
```

### Linux-Basics (für Windows-User)
```bash
ls -lah            # Dateien anzeigen (wie dir)
cd /app            # Verzeichnis wechseln
pwd                # Aktuelles Verzeichnis anzeigen
cat file.txt       # Datei anzeigen (wie type)
cp src dst         # Datei kopieren (wie copy)
mv src dst         # Datei verschieben (wie move)
rm file            # Datei löschen (wie del)
mkdir -p dir       # Ordner erstellen (wie md)
```

---

## 🚀 Fortgeschrittene Nutzung

### Container-Netzwerk debuggen
```bash
# IP-Adresse des Containers
ip addr show

# DNS testen
nslookup updates.vera-office.de

# Ping testen
ping -c 3 8.8.8.8
```

### Performance-Analyse
```bash
# Speicherverbrauch
free -h

# CPU-Last
top

# Disk-I/O
iostat

# Netzwerk-Traffic
iftop
```

### Multi-Container Setup (später)
```yaml
# docker-compose.yml erweitern:
services:
  backend:
    # ...
  
  frontend:
    build: ../frontend
    ports:
      - "80:80"
    depends_on:
      - backend
  
  database:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

## ✅ Checkliste: Sandbox funktioniert?

- [ ] Container läuft: `docker ps | findstr vera`
- [ ] Health Check OK: `curl http://localhost:8000/health`
- [ ] Kann einsteigen: `docker exec -it vera-backend bash`
- [ ] PowerShell verfügbar: `pwsh --version`
- [ ] Aliases funktionieren: `md`, `cls`, `ll`, `ps1`
- [ ] Tools verfügbar: `curl`, `wget`, `git`, `vim`, `htop`, `jq`, `tree`
- [ ] OCR importierbar: `python -c "import paddleocr"`
- [ ] Datenbank existiert: `ls -lah /app/data/vera.db`
- [ ] Logs schreibbar: `echo "test" >> /app/logs/test.log`

**Wenn ALLE ✓ → Sandbox ist ready! 🎉**

---

## 🆘 Support

**Probleme?**
1. Logs prüfen: `docker logs vera-backend --tail 100`
2. Container neu starten: `docker restart vera-backend`
3. Image neu bauen: `docker-compose up -d --build`
4. Alles zurücksetzen: `docker-compose down -v && docker-compose up -d --build`

**Immer noch Probleme?**
→ Erstelle Issue mit Logs + Fehlermeldung

---

**Happy Sandboxing! 🏖️**

*Javix | 2026-03-07*
