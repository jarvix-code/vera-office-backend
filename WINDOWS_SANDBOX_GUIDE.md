# VERA Office - Windows Sandbox Testing Guide

**Für:** Boris (Entwickler), Testing, sichere VERA-Tests  
**Zweck:** VERA in isolierter Windows-Umgebung testen ohne Haupt-Windows zu riskieren  
**Status:** ✅ Production-Ready

---

## 🎯 Was ist Windows Sandbox?

**Windows Sandbox** ist eine eingebaute Windows-Funktion (ab Windows 10 Pro):
- ✅ **Frisches Windows** in Sekunden (kein Setup!)
- ✅ **Komplett isoliert** (keine Gefahr für Haupt-System)
- ✅ **Automatisch gelöscht** beim Schließen (keine Spuren)
- ✅ **Leicht & schnell** (kein VirtualBox, kein Hyper-V Setup nötig)
- ✅ **Copy & Paste** funktioniert (Dateien reinziehen)

**Perfekt für:** VERA Installer testen, Bugs reproduzieren, Deployment-Test

---

## 🚀 Schnellstart (3 Schritte)

### 1️⃣ **Windows Sandbox aktivieren** (einmalig)

```powershell
# Als Administrator ausführen:
Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All

# Neustart erforderlich
Restart-Computer
```

**Oder manuell:**
- Windows-Features → "Windows-Sandbox" aktivieren → OK → Neustart

---

### 2️⃣ **Sandbox starten**

```powershell
# Doppelklick auf:
C:\Jarvix\vera-office\VERA-Sandbox.wsb
```

**Was passiert:**
- Windows Sandbox startet (frisches Windows 10/11)
- `C:\Jarvix\vera-office\` wird gemountet als `C:\VERA-Source\`
- `C:\VERA-Office-Installer\` wird gemountet als `C:\VERA-Installer\`
- VERA Installer startet automatisch

---

### 3️⃣ **Testen**

```
# In Sandbox:
1. Installer durchklicken
2. VERA starten
3. Dokument hochladen
4. Testen ob Bugs auftreten

# Fertig? Sandbox schließen = ALLES gelöscht
```

---

## 📋 Manuelle Nutzung (ohne .wsb)

### Start
```
Start → Windows Sandbox
```

### VERA Installer reinkopieren
**Option A: Drag & Drop**
- Installer von Windows in Sandbox-Fenster ziehen

**Option B: Netzwerk-Share**
- In Sandbox: `\\CASA_CODE\C$\VERA-Office-Installer\VERA-Office-Setup.exe`

**Option C: Copy & Paste**
- Installer kopieren (Strg+C)
- In Sandbox einfügen (Strg+V auf Desktop)

### Installieren & Testen
- Installer ausführen
- VERA starten (Desktop-Icon)
- Browser öffnet automatisch: `http://localhost:8000`

### Sandbox schließen
- Fenster schließen → "Änderungen verwerfen" → ALLES weg

---

## 🎯 Typische Use-Cases

### 1️⃣ **Installer testen** (vor Kunden-Deployment)

```
1. VERA-Sandbox.wsb öffnen
2. Installer läuft automatisch
3. Prüfen:
   - Installation erfolgreich?
   - Desktop-Icon vorhanden?
   - VERA startet?
   - Backend läuft?
   - Onboarding funktioniert?
4. Sandbox schließen
```

**Vorteil:** Siehst genau was Kunde sieht (frisches Windows!)

---

### 2️⃣ **Bug reproduzieren**

```
1. Sandbox starten
2. VERA installieren
3. Bug-Szenario nachstellen
4. Logs aus Sandbox kopieren (vor Schließen!)
5. Sandbox schließen
6. Fixes implementieren
7. Sandbox NEU starten → Testen ob gefixt
```

**Vorteil:** Saubere Umgebung für jeden Test!

---

### 3️⃣ **Dependencies testen**

```
1. Sandbox starten
2. VERA installieren
3. Prüfen:
   - OCR funktioniert? (paddleocr)
   - KI funktioniert? (Mistral 7B)
   - PDF-Generierung?
4. Sandbox schließen
```

**Vorteil:** Siehst ob Dependencies korrekt in Installer eingebunden sind!

---

### 4️⃣ **Multi-Version-Test**

```
# Version 1.0.0 testen:
1. Sandbox starten
2. VERA-v1.0.0.exe installieren
3. Testen

# Version 1.1.0 testen:
1. Sandbox NEU starten (automatisch frisch!)
2. VERA-v1.1.0.exe installieren
3. Testen
```

**Vorteil:** Keine Konflikte zwischen Versionen!

---

## 🛠️ VERA-Sandbox.wsb Konfiguration

**Inhalt:** `C:\Jarvix\vera-office\VERA-Sandbox.wsb`

```xml
<Configuration>
  <VGpu>Enable</VGpu>              <!-- GPU-Beschleunigung -->
  <Networking>Enable</Networking>   <!-- Internet-Zugriff -->
  
  <!-- Gemountete Ordner (Read-Only) -->
  <MappedFolders>
    <MappedFolder>
      <HostFolder>C:\Jarvix\vera-office</HostFolder>
      <SandboxFolder>C:\VERA-Source</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>C:\VERA-Office-Installer</HostFolder>
      <SandboxFolder>C:\VERA-Installer</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  
  <!-- Automatisch Installer starten beim Login -->
  <LogonCommand>
    <Command>C:\VERA-Installer\VERA-Office-Setup-v1.0.0.exe</Command>
  </LogonCommand>
</Configuration>
```

**Anpassungen:**
- `<HostFolder>` → Dein Windows-Pfad
- `<SandboxFolder>` → Pfad IN der Sandbox
- `<ReadOnly>` → `false` wenn du in Sandbox schreiben willst
- `<LogonCommand>` → Befehl der beim Start ausgeführt wird

---

## 📁 Dateien zwischen Sandbox & Host kopieren

### Host → Sandbox
**Während Sandbox läuft:**
- Drag & Drop in Sandbox-Fenster
- Copy & Paste (Strg+C → Strg+V)
- Gemountete Ordner (`C:\VERA-Source\`)

### Sandbox → Host (VOR Schließen!)
**Logs sichern:**
```powershell
# In Sandbox:
Copy-Item "C:\VERA-Office\logs\backend.log" "C:\VERA-Source\logs\sandbox-test.log"
```

**Nach Sandbox-Schließen:**
```powershell
# Auf Windows:
Get-Content "C:\Jarvix\vera-office\logs\sandbox-test.log"
```

---

## 🐛 Troubleshooting

### "Windows Sandbox kann nicht gestartet werden"

**Ursache:** Feature nicht aktiviert oder Hyper-V fehlt

**Lösung:**
```powershell
# Hyper-V aktivieren (falls noch nicht):
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All

# Windows Sandbox aktivieren:
Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All

# Neustart
Restart-Computer
```

---

### "VERA-Installer nicht gefunden"

**Ursache:** Pfad in `.wsb` falsch

**Lösung:**
```xml
<!-- Prüfe ob Pfad existiert: -->
C:\VERA-Office-Installer\VERA-Office-Setup-v1.0.0.exe

<!-- Falls nicht, ändere in VERA-Sandbox.wsb: -->
<HostFolder>C:\Dein\Pfad\Zum\Installer</HostFolder>
```

---

### "Keine Internetverbindung in Sandbox"

**Ursache:** Networking deaktiviert

**Lösung:**
```xml
<!-- In VERA-Sandbox.wsb: -->
<Networking>Enable</Networking>
```

---

### "Sandbox startet, aber VERA-Installer läuft nicht automatisch"

**Ursache:** LogonCommand fehlerhaft

**Lösung:**
```xml
<!-- Teste manuell in Sandbox: -->
C:\VERA-Installer\VERA-Office-Setup-v1.0.0.exe

<!-- Falls Pfad falsch, korrigiere in .wsb: -->
<LogonCommand>
  <Command>C:\VERA-Installer\VERA-Office-Setup-v1.0.0.exe</Command>
</LogonCommand>
```

---

## 🆚 Windows Sandbox vs. Docker vs. VM

| Feature | Windows Sandbox | Docker (Linux) | Hyper-V VM |
|---------|----------------|----------------|------------|
| **Geschwindigkeit** | ⚡ Sekunden | ⚡ Sekunden | 🐌 Minuten |
| **Windows-Kompatibilität** | ✅ 100% | ❌ Nein (Linux) | ✅ 100% |
| **Automatisch zurücksetzen** | ✅ Ja | ⚠️ Manuell | ⚠️ Snapshot |
| **Ressourcen** | 💾 Leicht (2 GB RAM) | 💾 Leicht (1 GB RAM) | 🏋️ Schwer (8 GB RAM) |
| **Setup** | ✅ 1 Befehl | ⚠️ Docker installieren | ⚠️ VM erstellen |
| **VERA-Testing** | ✅ Perfekt | ❌ Nur Linux | ✅ Gut (langsam) |

**Empfehlung für VERA:** Windows Sandbox (schnell, nativ Windows, perfekt für Testing)

---

## ✅ Checkliste: Sandbox ist ready

- [ ] Windows Sandbox aktiviert (`Enable-WindowsOptionalFeature`)
- [ ] Neustart durchgeführt
- [ ] VERA-Sandbox.wsb existiert
- [ ] Pfade in `.wsb` korrekt (Installer-Ordner)
- [ ] Doppelklick auf `.wsb` → Sandbox startet
- [ ] VERA Installer läuft automatisch
- [ ] Internet funktioniert in Sandbox
- [ ] Sandbox schließen → alles weg

**Wenn ALLE ✓ → Windows Sandbox ist ready für VERA-Testing! 🎉**

---

## 🎁 Bonus: PowerShell-Shortcuts

```powershell
# Sandbox starten (ohne .wsb):
Start-Process "WindowsSandbox.exe"

# VERA in Sandbox installieren (automatisiert):
Start-Process "C:\Jarvix\vera-office\VERA-Sandbox.wsb"

# Sandbox-Logs anschauen (nach Test):
Get-Content "C:\Jarvix\vera-office\logs\sandbox-test.log"
```

---

**Windows Sandbox ist bereit - viel Erfolg beim Testing! 🚀**

*Javix | 2026-03-07*
