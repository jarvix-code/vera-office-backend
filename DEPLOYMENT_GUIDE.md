# VERA Office - Deployment Guide

**Für:** Boris (CEO), Systemhaus-Techniker, DevOps  
**Status:** ✅ PRODUCTION-READY (nach Phase 1-3 Fixes)  
**Letzte Aktualisierung:** 2026-03-07

---

## 🎯 Schnellstart (3 Befehle)

```powershell
# 1. Dependencies installieren
cd installer
.\INSTALL_DEPS.ps1

# 2. Installer bauen
cd ..
.\BUILD_INSTALLER.ps1

# 3. Fertig! Installer liegt in C:\VERA-Office-Installer\
```

---

## 📋 Voraussetzungen

### Entwicklungsumgebung
- ✅ Windows 10/11 (x64)
- ✅ Node.js 18+ (für Frontend Build)
- ✅ Inno Setup 6 (für Installer-Kompilierung)
- ✅ Internetzugang (für npm + pip)

### Projekt-Dateien
- ✅ `frontend/` (Vue 3 App)
- ✅ `backend/` (FastAPI App)
- ✅ `installer/python-embed/` (Python 3.12 Embedded, entpackt)
- ✅ `installer/requirements.txt` (Dependencies-Liste)
- ✅ `models/mistral-7b-instruct-v0.2.Q4_K_M.gguf` (4 GB LLM-Modell)
- ⚠️ `keys/public.pem` (OPTIONAL, für Lizenz-Verifikation)

---

## 🛠️ Build-Prozess (manuell)

### Schritt 1: Frontend bauen

```powershell
cd frontend
npm install  # (nur beim ersten Mal)
npm run build
```

**Erwartetes Ergebnis:**
- `frontend/dist/` existiert
- `frontend/dist/index.html` vorhanden
- ~1 MB Gesamtgröße

**Troubleshooting:**
```powershell
# Fehler: "npm not found"
# → Node.js installieren von https://nodejs.org

# Fehler: "Build failed"
# → npm install erneut ausführen
# → node_modules/ löschen, npm install wiederholen
```

---

### Schritt 2: Dependencies in python-embed installieren

```powershell
cd installer
.\INSTALL_DEPS.ps1
```

**Was passiert:**
- `pip` wird aktualisiert
- Dependencies aus `requirements.txt` werden in `python-embed/Lib/site-packages/` installiert
- **Dauer:** 5-10 Minuten (je nach Internetgeschwindigkeit)

**Kritische Dependencies:**
- paddleocr==2.9.1 (OCR-Engine, ~500 MB)
- paddlepaddle==3.0.0b2 (PaddleOCR Backend, ~300 MB)
- opencv-python==4.10.0.84 (Bildverarbeitung, ~60 MB)
- numpy>=1.24.0 (Arrays, ~20 MB)

**Troubleshooting:**
```powershell
# Fehler: "pip install failed"
# → Proxy / Firewall prüfen
# → Manuell: python-embed\python.exe -m pip install -r requirements.txt --target python-embed\Lib\site-packages

# Fehler: "No space left"
# → Mindestens 2 GB freier Speicher in installer/ nötig
```

---

### Schritt 3: Public Key kopieren (OPTIONAL)

```powershell
# Falls vera-admin/ Projekt existiert:
copy D:\vera-admin\keys\public.pem .\keys\public.pem

# Falls nicht: Installer funktioniert trotzdem (Lizenz-Check disabled)
```

---

### Schritt 4: Installer kompilieren

```powershell
cd installer
& "C:\Program Files (x86)\Inno Setup 6\iscc.exe" vera-setup.iss
```

**Was passiert:**
- Inno Setup liest `vera-setup.iss`
- Kopiert alle Dateien (Python, Frontend, Backend, Models) in temporären Build-Ordner
- Komprimiert zu `.exe` Installer
- **Dauer:** 10-30 Minuten (Models sind 4 GB!)

**Erwartetes Ergebnis:**
- `C:\VERA-Office-Installer\VERA-Office-Setup-v1.0.0.exe` (~4-6 GB)
- Multi-Volume Setup (falls aktiviert: mehrere .bin Dateien)

**Troubleshooting:**
```powershell
# Fehler: "Source file not found"
# → Prüfe Pfade in vera-setup.iss (alle Pfade müssen RELATIV sein)
# → Prüfe ob frontend/dist/ existiert

# Fehler: "Inno Setup not found"
# → Installieren von https://jrsoftware.org/isdl.php

# Fehler: "Out of memory"
# → Models sind zu groß für RAM → DiskSpanning aktivieren (bereits in .iss)
```

---

## 🚀 Automatischer Build (empfohlen)

Nutze das fertige Build-Script:

```powershell
.\BUILD_INSTALLER.ps1
```

**Was es tut:**
1. ✅ Frontend Build (`npm run build`)
2. ✅ Dependencies Check (installiert bei Bedarf)
3. ✅ Public Key Check (warnt wenn fehlt)
4. ✅ Inno Setup Compile

**Ausgabe bei Erfolg:**
```
=====================================
  Installer Build ERFOLGREICH!
=====================================

Installer: C:\VERA-Office-Installer\VERA-Office-Setup-v1.0.0.exe
Größe: 4.2 GB

Nächste Schritte:
  1. Installer auf USB-Stick kopieren
  2. Auf frischer Windows-VM testen
  3. Beim Kunden installieren
```

---

## 📦 Installation beim Kunden

### Voraussetzungen
- Windows 10/11 (x64)
- Mindestens 8 GB RAM
- Mindestens 10 GB freier Speicher
- (Optional) Internetverbindung für Updates

### Installation

1. **USB-Stick einstecken**
2. **Installer starten:** `VERA-Office-Setup-v1.0.0.exe`
3. **Wizard durchlaufen:**
   - Installationspfad: `C:\VERA-Office` (Standard)
   - Optionen:
     - ✅ Desktop-Verknüpfung
     - ✅ Autostart bei Windows-Start
     - ⚠️ Auto-Login (nur für Plug-and-Play Tablet)
4. **Firewall-Regel:** Wird automatisch erstellt (Port 8000)
5. **VERA startet automatisch** nach Installation
6. **Browser öffnet:** `http://localhost:8000`

### Onboarding-Wizard

1. **Admin-Konto** erstellen (Benutzername + Passwort)
2. **Firmen-Profil** (Name, Branche, Mitarbeiteranzahl)
3. **Dokumenttypen** auswählen (vordefiniert nach Branche)
4. **Netzwerk** konfigurieren (optional)
5. **iPad verbinden:** QR-Code scannen → `https://vera-office.local`
6. **Lizenz aktivieren:**
   - Option A: 30-Tage Trial starten
   - Option B: Lizenz-Key eingeben
   - Connection-Test: "Verbindung zum Server testen"
7. **Fertig!** → VERA Dashboard

---

## 🧪 Testing-Checkliste

### Pre-Deployment (Entwicklungsrechner)

- [ ] Frontend Build erfolgreich (`dist/` existiert)
- [ ] Dependencies installiert (paddleocr, opencv vorhanden)
- [ ] Installer kompiliert ohne Fehler
- [ ] Installer-EXE existiert (4-6 GB)

### Post-Installation (frische Windows-VM)

- [ ] Installation erfolgreich (keine Fehler im Wizard)
- [ ] Desktop-Icon vorhanden
- [ ] VERA startet beim Doppelklick
- [ ] Browser öffnet automatisch `http://localhost:8000`
- [ ] Onboarding-Wizard lädt korrekt
- [ ] Admin-Konto erstellen funktioniert
- [ ] Trial-Lizenz wird aktiviert
- [ ] Dokument hochladen → OCR läuft (kein "ModuleNotFoundError")
- [ ] Dokument wird klassifiziert (Kategorie zugewiesen)
- [ ] Download-Button funktioniert
- [ ] "Kategorie korrigieren" Button funktioniert
- [ ] Sidebar zeigt Gruppen (Kern, QM, ERP, System)

### Kritische Fehlerszenarien

❌ **"ModuleNotFoundError: No module named 'paddleocr'"**  
→ Dependencies fehlen in python-embed → `INSTALL_DEPS.ps1` ausführen

❌ **"Connection-Test: Server nicht erreichbar"**  
→ Offline-Installation OK, aber Updates funktionieren nicht → Internetverbindung prüfen

❌ **Download-Button tut nichts**  
→ Backend-Endpoint fehlt → Phase 1 Fixes nicht angewendet

❌ **AI lernt nicht von Korrekturen**  
→ Feedback-UI fehlt → Phase 1 Fixes nicht angewendet

---

## 📊 Installer-Größe Breakdown

| Komponente | Größe | Notwendig? |
|------------|-------|-----------|
| Python Embedded + Dependencies | ~1.5 GB | ✅ Ja |
| Mistral 7B Q4 Model | ~4 GB | ✅ Ja (AI-Klassifikation) |
| PaddleOCR Models | ~100 MB | ✅ Ja (OCR) |
| Frontend (dist/) | ~1 MB | ✅ Ja |
| Backend | ~50 MB | ✅ Ja |
| **GESAMT** | **~5.7 GB** | |

**Warum so groß?**  
→ LLM-Modell (Mistral 7B) ist 4 GB → Für KI-Klassifikation notwendig → Komplett offline-fähig!

**Alternative (kleiner, aber nicht offline):**  
→ Mistral 7B weglassen → API-basierte Klassifikation (z.B. OpenAI GPT-4) → Installer nur ~1.7 GB

---

## 🔄 Update-Prozess

### Auto-Update (wenn Server erreichbar)

1. VERA prüft alle 24h auf Updates (`https://updates.vera-office.de`)
2. Falls Update verfügbar: Download im Hintergrund
3. Signatur-Verifikation (Ed25519)
4. Backup von `backend/`, `config/`, `frontend/`
5. Update installieren (ZIP entpacken)
6. VERA neu starten

**User-Benachrichtigung:**  
→ Toast-Notification: "Update verfügbar. Jetzt installieren?"

### Manuelles Update

1. Neuen Installer herunterladen
2. VERA beenden
3. Installer ausführen (überschreibt alte Version, behält `data/` bei)
4. VERA neu starten

---

## 🆘 Support & Troubleshooting

### Log-Dateien

| Datei | Pfad | Inhalt |
|-------|------|--------|
| **Backend Log** | `C:\VERA-Office\logs\backend.log` | FastAPI Errors, OCR-Pipeline, AI-Klassifikation |
| **Hotfolder Log** | `C:\VERA-Office\logs\hotfolder.log` | Scanner-Aktivität, neue Dokumente |
| **Installer Log** | `C:\VERA-Office\Setup.log` | Inno Setup Installation |

### Häufige Probleme

**Problem:** VERA startet nicht nach Installation  
**Lösung:**
```powershell
# Log prüfen:
Get-Content "C:\VERA-Office\logs\backend.log" -Tail 50

# Manuell starten (Debug):
cd C:\VERA-Office
.\start-vera.bat

# Erwartete Ausgabe: "VERA Office Backend bereit auf 0.0.0.0:8000"
```

**Problem:** OCR funktioniert nicht ("ModuleNotFoundError")  
**Lösung:**
```powershell
# Dependencies nachinstallieren:
cd C:\VERA-Office\python
.\python.exe -m pip install paddleocr paddlepaddle opencv-python
```

**Problem:** Firewall blockiert Port 8000  
**Lösung:**
```powershell
# Firewall-Regel manuell erstellen:
netsh advfirewall firewall add rule name="VERA Office" dir=in action=allow protocol=TCP localport=8000
```

**Problem:** iPad kann VERA nicht erreichen  
**Lösung:**
- Prüfen: Gleiches WLAN?
- Prüfen: Windows Firewall erlaubt Port 8000?
- Prüfen: `https://vera-office.local` erreichbar? (SSL-Warnung OK = Server läuft)

---

## 📞 Kontakt

**Support:** support@vera-office.de  
**Dokumentation:** https://docs.vera-office.de  
**Updates:** https://updates.vera-office.de

---

**Viel Erfolg beim Deployment! 🚀**

*Javix | 2026-03-07*
