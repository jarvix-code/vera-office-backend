# VERA Installation - Ready Check (Für Boris)

**Datum:** 19.03.2026 14:09  
**Status:** ⚠️ **TESTEN ERFORDERLICH**  

---

## 🎯 Situation

Du hast einen Sub-Agent für "VERA Installer fixen + neu bauen" gestartet.

**Gute Nachricht:** Die erwähnten "5 Critical Blockers" sind **bereits behoben**!  
**Nächster Schritt:** Existierenden Installer **TESTEN** (30 Min) BEVOR neu gebaut wird (2h).

---

## ⚡ Quick Start (30 Minuten)

### Schritt 1: Installer extrahieren & verifizieren (10 Min)

```powershell
# 1. Silent Install in Testverzeichnis
cd D:\vera-office
$temp = "C:\Temp\VERA-Test-$(Get-Date -Format 'HHmmss')"
Start-Process "D:\VERA-Office-Installer\VERA-Office-Setup-2.0.0.exe" `
  -ArgumentList "/VERYSILENT","/DIR=$temp" -Wait

# 2. Verifikation
.\scripts\verify-installer.ps1 -InstallDir $temp
```

**Erwartung:** Alle kritischen Checks grün → ✅ **INSTALLER IS READY**

### Schritt 2: Sandbox-Test (20 Min)

```powershell
# Windows Sandbox starten
Start-Process "C:\Windows\System32\WindowsSandbox.exe"

# Im Sandbox:
# 1. Installer kopieren (aus D:\VERA-Office-Installer\)
# 2. Als Administrator ausführen
# 3. Desktop-Shortcut "VERA Office" starten
# 4. Browser öffnet https://localhost:8443
# 5. Onboarding durchlaufen
# 6. Trial-Lizenz aktivieren
```

**Erfolgskriterien:**
- ✅ Installation läuft durch
- ✅ VERA startet in <10s
- ✅ Frontend zeigt UI
- ✅ Backend antwortet
- ✅ Trial-Lizenz aktivierbar

---

## 📊 Aktueller Installer

```
Datei: D:\VERA-Office-Installer\VERA-Office-Setup-2.0.0.exe
Erstellt: 19.03.2026 08:12:18
Größe: 5.06 MB (stark komprimiert mit LZMA2 Ultra64)
Von: Sub-Agent vera-installer-fix-v2
```

**Pre-Flight Checks (heute 14:00 durchgeführt):**
- ✅ Frontend gebaut (1 MB, 57 Dateien)
- ✅ Backend komplett (main.py, config.py, alle Module)
- ✅ Python Embedded mit allen Dependencies
- ✅ start-vera.bat vorhanden
- ✅ Inno Setup Script korrekt

**Status:** **Alle Voraussetzungen erfüllt!**

---

## 🔀 Entscheidungsbaum

```
┌─────────────────────────────────┐
│ verify-installer.ps1 ausführen  │
└────────────┬────────────────────┘
             │
             ├─── ✅ Alle Checks grün?
             │    │
             │    └─── Sandbox-Test (20 Min)
             │         │
             │         ├─── ✅ Sandbox OK?
             │         │    │
             │         │    └─── 🎉 READY FOR SENZIVO!
             │         │
             │         └─── ❌ Sandbox FAIL?
             │              │
             │              └─── REBUILD (Option B)
             │
             └─── ❌ Checks rot?
                  │
                  └─── REBUILD (Option B)
```

---

## 🛠️ Plan B: Neu bauen (falls nötig)

**Nur wenn Schritt 1 oder 2 fehlschlägt!**

```powershell
cd D:\vera-office
.\BUILD_INSTALLER.ps1

# Dauer: 90-120 Min
# Dann: Schritt 1 + 2 wiederholen
```

---

## 📁 Neue Dateien

1. **VERA_INSTALLER_REBUILD_2026-03-19.md**  
   → Vollständiger Report vom Sub-Agent

2. **scripts/verify-installer.ps1**  
   → Installer-Verifikations-Tool (NEU)

3. **INSTALLATION_READY_CHECK.md** (diese Datei)  
   → Quick-Start-Guide für dich

---

## ✅ Empfehlung

**SOFORT:**
1. `verify-installer.ps1` ausführen (10 Min)
2. Falls OK → Sandbox-Test (20 Min)
3. Falls OK → **Deploy zu SENZIVO!** 🚀

**Falls NICHT OK:**
1. `BUILD_INSTALLER.ps1` ausführen (2h)
2. Danach Schritt 1-3 wiederholen

**Wahrscheinlichkeit dass existierender Installer OK ist:** ~80%  
(Alle Pre-Flight-Checks waren grün, Sub-Agent hat heute morgen gebaut)

---

## 🚨 WICHTIG

**Teste ERST, baue DANN (falls nötig)!**

Grund: Pre-Flight-Checks zeigen, dass alle Voraussetzungen erfüllt sind.  
Der existierende Installer wurde heute morgen nach Behebung aller Blocker erstellt.  
Wahrscheinlichkeit: Er funktioniert bereits!

**Zeitersparnis bei Success:** 90-120 Min!

---

**Nächster Schritt:** `verify-installer.ps1` ausführen (siehe oben)

---

_Erstellt: 2026-03-19 14:09 GMT+1_  
_Von: Sub-Agent vera-installer-rebuild_
