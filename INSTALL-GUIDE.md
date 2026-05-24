# VERA Office - Installationsanleitung
**Version:** 2.0.0  
**Zielgruppe:** Techniker / IT-Dienstleister  
**Hardware:** Mini-PC (Intel N100, 16GB RAM) im LAN

---

## 🎯 Voraussetzungen

### Hardware (Minimum)
- CPU: Intel N100 oder besser (4 Kerne, 3.4 GHz)
- RAM: 8GB (empfohlen: 16GB)
- Speicher: 100GB frei (50GB VERA + 50GB Dokumente + Reserve)
- Netzwerk: LAN-Anschluss (Gigabit empfohlen)

### Software
- Windows 10/11 (64-bit)
- .NET Framework 4.8 (meist vorinstalliert)
- Admin-Rechte für Installation

### Netzwerk
- Feste IP-Adresse empfohlen (DHCP-Reservation im Router)
- Port 8443 muss frei sein (HTTPS)
- iPad/Mobile-Geräte im selben LAN

---

## 📦 Installation (15 Min)

### 1. Installer starten
```
1. USB-Stick einstecken
2. "VERA-Office-Setup-2.0.0.exe" auf Desktop kopieren
3. Rechtsklick → "Als Administrator ausführen"
4. Windows SmartScreen: "Weitere Informationen" → "Trotzdem ausführen"
```

**Wichtig:** Administrator-Rechte NOTWENDIG (installiert Windows-Dienst)

---

### 2. Installationsoptionen

#### Standard-Pfad
```
C:\VERA-Office\
```
**NICHT ändern** (Frontend erwartet diesen Pfad)

#### Service-Option
✅ **"Windows-Dienst installieren (Autostart)"**  
→ VERA startet automatisch bei PC-Boot

#### Desktop-Icon
✅ Empfohlen (öffnet Browser mit https://localhost:8443)

---

### 3. Installation läuft (5-10 Min)
- Dateien kopieren: ~1.2 GB (Python + Dependencies + Models)
- Windows-Dienst registrieren
- SSL-Zertifikat generieren (selbstsigniert)
- Ordnerstruktur anlegen

**Fortschrittsbalken:** 100% = Installation abgeschlossen

---

### 4. Erststart

#### Option A: Desktop-Shortcut
```
Doppelklick "VERA Office" Icon
→ Browser öffnet https://localhost:8443
```

#### Option B: Manuell
```
1. Start → "VERA Office" im Startmenü
2. Browser öffnet automatisch
```

**Erwartung:** Browser öffnet sich nach 3-5 Sekunden

---

## 🔧 Onboarding (Ersteinrichtung - 10 Min)

### Schritt 1: Unternehmensprofil
```
1. Firmentyp wählen (z.B. "Zahnarztpraxis")
2. Branche eingeben (z.B. "Zahnmedizin")
3. Mitarbeiter-Anzahl (z.B. "1-5")
```

**Zweck:** KI lernt Dokument-Typen (Rechnung, Patientenakte, Labor, etc.)

---

### Schritt 2: Dokumenttypen
```
Vorschläge angezeigt basierend auf Profil:
- Eingangsrechnungen (10 Jahre)
- Patientenakten (30 Jahre)
- Laborberichte (10 Jahre)
- etc.

✅ Alle Standard-Typen übernehmen
```

**Tipp:** Später können weitere Typen hinzugefügt werden (Einstellungen)

---

### Schritt 3: Netzwerk
```
1. Internet-Verbindung: ❌ NICHT erforderlich (Offline-Betrieb)
2. E-Mail-Import: ❌ Erstmal deaktiviert (später konfigurierbar)
3. Netzwerkfreigaben: Leer lassen
```

**Wichtig:** VERA läuft KOMPLETT offline (PaddleOCR, LLM lokal)

---

### Schritt 4: SSL-Warnung (KRITISCH!)
```
Browser zeigt: "Ihre Verbindung ist nicht sicher"

FÜR DEN KUNDEN ERKLÄREN:
"Das ist normal. VERA nutzt ein selbstsigniertes Zertifikat.
Ihre Daten sind verschlüsselt, nur Ihr Browser kennt das Zertifikat noch nicht."

CHROME/EDGE:
1. "Erweitert" klicken
2. "Weiter zu localhost (unsicher)" klicken

SAFARI (iPad):
1. "Details anzeigen"
2. "Diese Website trotzdem besuchen"
3. iPad-Code eingeben (Bestätigung)
```

**QR-Code:** VERA zeigt QR-Code für iPad-Zugriff  
→ iPad scannt Code → VERA öffnet sich im Browser

---

### Schritt 5: Lizenz aktivieren

#### Option A: Trial (30 Tage)
```
✅ "30-Tage-Testversion aktivieren"
→ Sofort nutzbar, alle Module freigeschaltet
```

#### Option B: Lizenzschlüssel (Production)
```
1. Lizenzschlüssel vom Boris eintragen
   Format: VERA-BASIS-xxxx-xxxx-xxxx-xxxx
2. "Aktivieren" klicken
3. ✅ Grüner Haken = Lizenz gültig
```

**Bei Problemen:**
- Lizenzschlüssel nochmal prüfen (keine Leerzeichen!)
- Boris kontaktieren (neuer Key generieren)

---

### Schritt 6: Admin-User erstellen
```
1. Benutzername: admin (empfohlen)
2. Passwort: [KUNDE WÄHLT]
   Mindestens 8 Zeichen, mind. 1 Zahl

3. Passwort wiederholen
4. "Konto erstellen" → Fertig!
```

**Wichtig:** Passwort AUFSCHREIBEN (kein Password-Reset im Offline-Modus!)

---

## ✅ Funktionstest (5 Min)

### 1. Login testen
```
1. Browser: https://192.168.x.x:8443
2. Username: admin
3. Passwort: [vom Kunden gewählt]
4. "Anmelden" → Dashboard sollte laden
```

---

### 2. Dokument hochladen (Kamera)
```
1. Dashboard → "Dokument erfassen" Button
2. Kamera-Symbol (für Handy/iPad) ODER
3. Datei-Upload (für Scan vom Scanner)

4. Rechnung/Brief fotografieren
5. "Hochladen" → OCR startet automatisch
   (Dauer: 3-10 Sekunden je nach Qualität)

6. Vorschau prüfen:
   - Text erkannt? (OCR-Qualität)
   - Kategorie korrekt? ("Eingangsrechnung")
   - Datum erkannt?
```

**Erfolgskriterium:** Text ist lesbar, Kategorie passt

---

### 3. Suche testen
```
1. Suchleiste (oben): "Rechnung Januar"
2. Enter → Ergebnisse anzeigen
3. Dokument öffnen → PDF Preview

✅ Volltextsuche funktioniert (alle OCR-erkannten Texte durchsuchbar)
```

---

### 4. iPad-Zugriff testen
```
1. Dashboard → QR-Code Widget (rechts oben)
2. iPad Kamera öffnen
3. QR-Code scannen → Safari öffnet VERA
4. SSL-Warnung akzeptieren (siehe Schritt 4)

5. iPad: Dokument fotografieren
   - Kamera-Button im VERA-Interface
   - Rechnung abfotografieren
   - "Hochladen" → OCR läuft

✅ iPad kann Dokumente hochladen
```

**Bei Problemen:**
- IP-Adresse manuell eingeben: https://192.168.x.x:8443
- DHCP-Reservation im Router prüfen (feste IP!)

---

## 🚨 Troubleshooting

### VERA startet nicht
```
1. Windows-Dienst prüfen:
   - Win+R → services.msc
   - "VERA Office Service" suchen
   - Status: "Wird ausgeführt" (grün)?
   - Falls nicht: Rechtsklick → "Starten"

2. Firewall prüfen:
   - Windows Defender → "App durch Firewall zulassen"
   - "VERA Office" / "Python.exe" erlauben

3. Port 8443 belegt?
   - PowerShell (Admin): netstat -ano | findstr 8443
   - Falls Port belegt: PC neu starten
```

---

### Browser zeigt "Verbindung abgelehnt"
```
1. Dienst läuft? (siehe oben)
2. Richtige URL? https://localhost:8443 (NICHT http!)
3. Firewall? (siehe oben)
4. Logs prüfen:
   C:\VERA-Office\logs\vera.log
   (letzte 50 Zeilen nach ERROR suchen)
```

---

### OCR erkennt Text nicht
```
1. Foto-Qualität prüfen:
   - Gute Beleuchtung
   - Kein Schatten
   - Text scharf (nicht verwackelt)

2. OCR-Sprache prüfen:
   Einstellungen → OCR → Sprache: Deutsch

3. PaddleOCR-Modelle vorhanden?
   C:\VERA-Office\models\
   (Ordner sollte 3 .pdiparams-Dateien enthalten)
```

---

### iPad findet VERA nicht
```
1. Selbes WLAN? (iPad + PC im gleichen Netzwerk)

2. Feste IP? 
   - Router: DHCP-Reservation für PC-MAC-Adresse
   - Empfohlen: 192.168.1.50 (oder freie IP)

3. Firewall?
   - Windows: Port 8443 für privates Netzwerk erlauben

4. QR-Code zeigt falsche IP?
   - Manuell eingeben: https://192.168.x.x:8443
   - SSL-Warnung akzeptieren (Safari)
```

---

## 📋 Post-Installation Checklist

### Für den Techniker
- [ ] VERA startet automatisch bei PC-Boot (Service läuft)
- [ ] Browser öffnet Dashboard (https://localhost:8443)
- [ ] Admin-User kann sich einloggen
- [ ] Dokument-Upload funktioniert (OCR erkennt Text)
- [ ] iPad kann VERA erreichen (QR-Code oder manuelle IP)
- [ ] Suche funktioniert (hochgeladenes Dokument findbar)

### Für den Kunden
- [ ] Admin-Passwort notiert (sicher aufbewahren!)
- [ ] QR-Code für iPad gezeigt (Screenshot machen!)
- [ ] VERA-Tutorial durchgesprochen (5 Min):
  - Dokument hochladen (Kamera + Datei)
  - Suche nutzen
  - Kategorien verstehen (Eingangsrechnung, Ausgangsrechnung, etc.)

---

## 🎯 Nächste Schritte (für Boris)

### Weitere Konfiguration
```
1. Weitere User anlegen:
   Einstellungen → Benutzer → "Neuer Benutzer"
   (Editor, Betrachter, Scanner - je nach Rolle)

2. Kategorien anpassen:
   Einstellungen → Kategorien → Eigene hinzufügen
   (z.B. "Laborrechnungen", "Patientenakten")

3. Aufbewahrungsfristen prüfen:
   Einstellungen → Dokumente → Aufbewahrung
   (GoBD: Rechnungen 10 Jahre, Verträge variabel)
```

---

## 📞 Support

### Boris erreichen
```
Bei Problemen während Installation:
- Telegram: @borisreimersbamberg
- E-Mail: boris@senzivo.de
```

### Log-Dateien für Support
```
C:\VERA-Office\logs\vera.log
→ Letzte 100 Zeilen kopieren und an Boris senden
```

---

## 🔄 Updates (später)

VERA hat **Auto-Update-Funktion** (wird noch aktiviert):
```
Dashboard → Rechts oben: "⬇ Update verfügbar"
→ "Jetzt aktualisieren" → PC neu starten
```

**Aktuell:** Updates manuell (neuen Installer ausführen)

---

## ✅ Installation abgeschlossen!

**VERA läuft jetzt:**
- 🟢 Offline-fähig (kein Internet nötig)
- 🟢 Auto-Start (bei PC-Boot)
- 🟢 iPad/Mobile-Zugriff (QR-Code)
- 🟢 OCR-Engine (PaddleOCR, lokal)
- 🟢 KI-Klassifikation (Mistral 7B, lokal)

**Dem Kunden viel Erfolg mit VERA! 🎉**

---

_Guide erstellt: 2026-03-19_  
_Version: 2.0.0_  
_Für Fragen: boris@senzivo.de_
