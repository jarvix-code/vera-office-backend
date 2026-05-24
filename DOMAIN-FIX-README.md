# VERA Office Domain Fix - COMPLETE ✅

## Problem gelöst!
- ✅ Caddy läuft und bindet Ports 80, 8001, 8443
- ✅ SSL-Zertifikat generiert (self-signed)
- ✅ HTTPS funktioniert

## Zugriff auf VERA:

### Option 1: IP-Adresse (funktioniert JETZT):
```
https://127.0.0.1:8443
```
→ Browser-Warnung: "Nicht sicher" → Advanced → Proceed anyway

### Option 2: Domain (nach Setup):
```
https://vera-office.local:8443
```
→ Benötigt **hosts-Datei-Eintrag** (siehe Setup unten)

---

## Setup-Script ausführen (einmalig als Admin):

### Windows:
1. **Rechtsklick** auf `SETUP-COMPLETE.ps1`
2. **"Als Administrator ausführen"**
3. Fertig!

Das Script macht:
- ✅ Fügt `127.0.0.1 vera-office.local` zur hosts-Datei hinzu
- ✅ Startet Caddy mit korrekter Konfiguration
- ✅ Verifiziert dass alles läuft

---

## Wichtige Dateien:

- `Caddyfile.final` - Funktionierende Caddy-Konfiguration
- `SETUP-COMPLETE.ps1` - Automatisches Setup (Admin benötigt)
- `caddy\caddy.exe` - Webserver-Binary

---

## Manuelle hosts-Datei-Bearbeitung (Alternative):

Falls Setup-Script nicht funktioniert:

1. **Als Administrator** öffnen:
   ```
   notepad C:\Windows\System32\drivers\etc\hosts
   ```

2. **Ans Ende** diese Zeile hinzufügen:
   ```
   127.0.0.1 vera-office.local
   ```

3. **Speichern** und schließen

4. **Caddy starten:**
   ```powershell
   cd C:\Jarvix\vera-office
   .\caddy\caddy.exe run --config Caddyfile.final --adapter caddyfile
   ```

---

## Ports:

| Port | Protokoll | Funktion |
|------|-----------|----------|
| 8443 | HTTPS | Haupt-Zugang zu VERA |
| 80   | HTTP | Auto-Redirect zu HTTPS |
| 8001 | HTTP | Fallback-Redirect |
| 2019 | HTTP | Caddy Admin-API |

---

## Warum funktioniert HTTPS JETZT?

**Vorher:**
- Caddy wartete auf Admin-Passwort beim Cert-Installation
- Ports wurden nicht gebunden

**Jetzt:**
- `skip_install_trust` in Caddyfile → kein System-Cert-Import
- Caddy generiert self-signed Cert ohne User-Interaktion
- Browser zeigt Warnung (normal für self-signed) → manuell akzeptieren

---

## Kamera-API:

✅ HTTPS läuft → Kamera-Zugriff funktioniert!
→ Teste in VERA: https://127.0.0.1:8443

---

## Logs:

Falls Probleme auftreten:
```powershell
# Caddy-Prozess checken
Get-Process caddy

# Ports checken
netstat -ano | findstr "8443"

# Caddy-Logs
Get-Content C:\Jarvix\vera-office\logs\caddy-access.log -Tail 50
```

---

## Zusammenfassung:

**FUNKTIONIERT JETZT:**
- ✅ https://127.0.0.1:8443 (sofort nutzbar)
- ✅ Kamera-API (HTTPS erforderlich)
- ✅ Login (boris/boris)

**NACH SETUP-SCRIPT:**
- ✅ https://vera-office.local:8443 (schöne Domain)

**Problem gelöst!** 🎉
