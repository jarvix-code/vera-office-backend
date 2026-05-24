# VERA Office - Trusted HTTPS Certificate Setup

## Problem
- Self-signed Certificate → Browser blockiert APIs (Camera, File System, Scanner)
- Browser zeigt Warnung "Nicht sicher"
- Moderne Web-APIs (Camera API, File System Access API) funktionieren NICHT

## Lösung: mkcert (Lokaler Trusted Certificate)

**Warum mkcert?**
- ✅ Funktioniert im LAN (keine Public IP nötig wie bei Let's Encrypt)
- ✅ Browser vertraut automatisch (Root-CA wird installiert)
- ✅ Einfacher als Let's Encrypt DNS-Challenge
- ✅ Perfekt für Entwicklung & lokale Praxis-Setups
- ✅ Keine Kosten, keine Domain nötig

## Installation (Einmalig, 5 Minuten)

### Schritt 1: PowerShell als Administrator öffnen
```powershell
# Rechtsklick auf PowerShell-Icon → "Als Administrator ausführen"
```

### Schritt 2: Setup-Script ausführen
```powershell
cd C:\Jarvix\vera-office
.\setup-trusted-cert.ps1
```

**Was das Script macht:**
1. Lädt mkcert herunter (falls nicht vorhanden)
2. Installiert lokale Root-CA (Browser vertraut dann automatisch)
3. Erstellt `frontend/cert/` Verzeichnis
4. Generiert Certificates für:
   - `192.168.178.44` (LAN IP)
   - `localhost`
   - `127.0.0.1`
   - `::1` (IPv6 localhost)
5. Aktualisiert `vite.config.ts` (ersetzt PFX durch key+cert)

### Schritt 3: Vite Dev Server neu starten
```powershell
cd C:\Jarvix\vera-office\frontend
npm run dev
```

### Schritt 4: Browser öffnen
```
https://192.168.178.44:5173
```

**Erwartetes Ergebnis:**
- ✅ Browser zeigt "Sicher" 🔒 (kein Warnung!)
- ✅ Camera API funktioniert
- ✅ File System Access API funktioniert
- ✅ Scanner-Integration ready

## Technische Details

### mkcert vs. Let's Encrypt

| Feature | mkcert | Let's Encrypt |
|---------|--------|---------------|
| **LAN-Setup** | ✅ Ja | ❌ Nein (braucht Public IP) |
| **Browser Trust** | ✅ Automatisch (nach Root-CA Install) | ✅ Automatisch |
| **Renewal** | ⏰ Alle ~10 Jahre | ⏰ Alle 90 Tage |
| **Setup-Komplexität** | ✅ Einfach (1 Script) | ❌ Komplex (DNS-Challenge, Certbot) |
| **Für Produktion** | ❌ Nein (nur Entwicklung/LAN) | ✅ Ja |
| **Kosten** | ✅ Kostenlos | ✅ Kostenlos |

**Empfehlung für VERA:**
- **Entwicklung/Praxis-LAN:** mkcert (du bist hier!)
- **Cloud-Hosting (später):** Let's Encrypt

### Was passiert technisch?

1. **Root-CA Installation:**
   - mkcert erstellt eine lokale Certificate Authority (CA)
   - Diese CA wird in Windows Trusted Root Store installiert
   - Alle Browser (Chrome, Edge, Firefox) vertrauen diesem Store
   - → Alle von mkcert erstellten Zertifikate werden automatisch vertraut

2. **Certificate Generation:**
   - mkcert erstellt ein Zertifikat für 192.168.178.44 + localhost
   - Zertifikat ist signiert von der lokalen CA
   - Browser prüft: Signatur von vertrauenswürdiger CA? → ✅ Ja → Grünes Schloss!

3. **Vite Integration:**
   - Vite nutzt `https.createServer()` (Node.js)
   - Benötigt `key` (Private Key) + `cert` (Certificate)
   - Vorher: PFX-Format (self-signed)
   - Nachher: PEM-Format (mkcert-signed)

### Dateistruktur nach Setup

```
frontend/
├── cert/
│   ├── 192.168.178.44+3.pem          # Certificate (public)
│   └── 192.168.178.44+3-key.pem      # Private Key (NICHT committen!)
└── vite.config.ts                     # Updated config
```

**⚠️ WICHTIG:** Private Key NIEMALS ins Git Repository committen!

### Browser-Kompatibilität

| Browser | Unterstützt mkcert Root-CA? |
|---------|----------------------------|
| Chrome (Windows/Mac/Linux) | ✅ Ja |
| Edge (Windows/Mac/Linux) | ✅ Ja |
| Firefox (Windows/Mac/Linux) | ✅ Ja |
| Safari (macOS) | ✅ Ja |

## Troubleshooting

### "Root-CA Installation fehlgeschlagen"
→ Script muss als **Administrator** laufen!

**Lösung:**
```powershell
# Rechtsklick auf PowerShell → "Als Administrator ausführen"
cd C:\Jarvix\vera-office
.\setup-trusted-cert.ps1
```

### "Certificate files not found"
→ mkcert konnte Certs nicht erstellen. Prüfe ob `C:\Jarvix\vera-office\mkcert.exe` vorhanden ist.

**Lösung:**
```powershell
# Prüfe ob mkcert existiert
Test-Path C:\Jarvix\vera-office\mkcert.exe
# Falls nicht → Script nochmal laufen lassen
```

### Browser zeigt immer noch Warnung
→ Browser neu starten (Root-CA wird erst nach Neustart vertraut)

**Lösung:**
```
1. Browser KOMPLETT schließen (alle Fenster!)
2. Browser neu öffnen
3. https://192.168.178.44:5173 aufrufen
```

### Vite startet nicht (HTTPS Error)
→ Prüfe ob `frontend/cert/*.pem` Dateien existieren

**Lösung:**
```powershell
# Prüfe Cert-Dateien
Get-ChildItem C:\Jarvix\vera-office\frontend\cert

# Falls leer → Script nochmal laufen lassen
```

### Vite nutzt immer noch altes PFX-Cert
→ `vite.config.ts` manuell prüfen

**Lösung:**
```powershell
# Öffne vite.config.ts
code C:\Jarvix\vera-office\frontend\vite.config.ts

# Server-Block sollte so aussehen:
server: {
  https: {
    key: fs.readFileSync(path.resolve(__dirname, 'cert/192.168.178.44+3-key.pem')),
    cert: fs.readFileSync(path.resolve(__dirname, 'cert/192.168.178.44+3.pem'))
  }
}
```

## Weitere Geräte (iPads, andere PCs)

### Andere Windows-PCs im LAN
1. Root-CA exportieren:
   ```powershell
   C:\Jarvix\vera-office\mkcert.exe -CAROOT
   # → Zeigt Pfad zur Root-CA (rootCA.pem)
   ```
2. `rootCA.pem` auf anderen PC kopieren (USB-Stick, Netzwerk, E-Mail)
3. Doppelklick auf `rootCA.pem` → "Zertifikat installieren"
4. Speicherort: "Vertrauenswürdige Stammzertifizierungsstellen"
5. Browser neu starten
6. `https://192.168.178.44:5173` → sollte jetzt "Sicher" zeigen

### iPads / iPhones
1. Root-CA per E-Mail/AirDrop verschicken
2. Profil installieren:
   - Einstellungen → Profil geladen → Installieren
3. Zertifikat aktivieren:
   - Einstellungen → Allgemein → Info → Zertifikatvertrauensstellungen
   - Schalter bei "mkcert" aktivieren
4. Safari öffnen → `https://192.168.178.44:5173`
5. Sollte ohne Warnung laden

### Android
1. Root-CA kopieren (via USB/E-Mail)
2. Einstellungen → Sicherheit → Verschlüsselung & Anmeldedaten
3. "Zertifikat installieren"
4. "CA-Zertifikat" wählen
5. Warnung akzeptieren
6. `rootCA.pem` auswählen
7. Chrome öffnen → `https://192.168.178.44:5173`
8. Sollte ohne Warnung laden

## Renewal (Certificates ablaufen nach ~10 Jahren)

mkcert-Zertifikate haben eine Gültigkeit von ca. **10 Jahren** (viel länger als Let's Encrypt 90 Tage!).

**Renewal-Prozess (wenn nötig):**
```powershell
cd C:\Jarvix\vera-office\frontend\cert
C:\Jarvix\vera-office\mkcert.exe 192.168.178.44 localhost 127.0.0.1 ::1
# → Neue Certs werden erstellt (überschreibt alte)

# Vite neu starten
cd C:\Jarvix\vera-office\frontend
npm run dev
```

## Backup

**⚠️ WICHTIG:** `rootCA.pem` + `rootCA-key.pem` sichern!

Diese Dateien sind die Master-CA für alle mkcert-Zertifikate. Ohne sie müssen alle Geräte neu konfiguriert werden!

**Backup-Prozess:**
```powershell
# Finde Root-CA Pfad
C:\Jarvix\vera-office\mkcert.exe -CAROOT
# → z.B. C:\Users\jarvi\AppData\Local\mkcert

# Kopiere BEIDE Dateien an sicheren Ort (USB, Cloud, etc.)
Copy-Item "C:\Users\jarvi\AppData\Local\mkcert\rootCA.pem" "D:\Backup\"
Copy-Item "C:\Users\jarvi\AppData\Local\mkcert\rootCA-key.pem" "D:\Backup\"
```

**⚠️ NIEMALS `rootCA-key.pem` teilen oder ins Git committen!** Das ist der Private Key der CA.

## Let's Encrypt Alternative (für Produktion)

Falls VERA später über öffentliche Domain erreichbar sein soll (z.B. `vera.praxis-beispiel.de`):

### Voraussetzungen
- Öffentliche Domain (z.B. über DynDNS: Duck DNS, No-IP)
- DNS-Zugriff für TXT-Record (für DNS-Challenge)
- Certbot installiert

### Setup
```powershell
# Certbot installieren (benötigt Chocolatey)
choco install certbot -y

# Cert anfordern (DNS-Challenge für LAN-Setup)
certbot certonly --manual --preferred-challenges dns -d vera.praxis-beispiel.de

# Certbot gibt TXT-Record vor → bei DNS-Provider eintragen
# → Warten bis DNS propagiert
# → Certbot verifiziert → Cert wird erstellt

# Cert nach VERA kopieren
Copy-Item "C:\Certbot\live\vera.praxis-beispiel.de\fullchain.pem" "C:\Jarvix\vera-office\frontend\cert\"
Copy-Item "C:\Certbot\live\vera.praxis-beispiel.de\privkey.pem" "C:\Jarvix\vera-office\frontend\cert\"

# vite.config.ts anpassen
# https: {
#   key: fs.readFileSync('./cert/privkey.pem'),
#   cert: fs.readFileSync('./cert/fullchain.pem')
# }
```

**ABER:** Let's Encrypt braucht öffentliche Erreichbarkeit (Port 80/443) → für LAN-Setup NICHT empfohlen!

## Status
- ✅ Setup-Script erstellt: `setup-trusted-cert.ps1`
- ⏳ **Nächster Schritt:** Script als Admin ausführen
- ⏳ Vite neu starten
- ⏳ Browser testen

## Support
Bei Problemen: Javix fragen (ich bin immer da! 🎯)

---

*Created: 2026-03-27*  
*Updated: 2026-03-27*
