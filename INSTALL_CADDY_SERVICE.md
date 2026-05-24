# Caddy als Windows Service (für Standard-Ports 80/443)

**Problem:** `vera-office.local` (ohne Port) braucht Standard-Ports 80 (HTTP) und 443 (HTTPS).  
**Windows:** Port 80/443 brauchen Admin-Rechte!

**Lösung:** Caddy als Windows Service mit Admin-Rechten laufen lassen.

---

## Installation (EINMALIG, braucht Admin-PowerShell)

### 1. Admin-PowerShell öffnen
```powershell
# Rechtsklick auf PowerShell → "Als Administrator ausführen"
```

### 2. Caddy Service erstellen
```powershell
cd C:\Jarvix\vera-office

sc.exe create CaddyVERA `
  binPath= "C:\Jarvix\vera-office\caddy\caddy.exe run --config C:\Jarvix\vera-office\Caddyfile" `
  start= auto `
  DisplayName= "Caddy VERA Office HTTPS Proxy"
```

### 3. Service starten
```powershell
sc.exe start CaddyVERA
```

### 4. Service-Status prüfen
```powershell
sc.exe query CaddyVERA
```

**Erwartung:**
```
STATE              : 4  RUNNING
```

### 5. Firewall (Falls Windows Firewall Port blockiert)
```powershell
New-NetFirewallRule -DisplayName "VERA Office HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
New-NetFirewallRule -DisplayName "VERA Office HTTP Redirect" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
```

---

## Test

**Browser (am PC):**
```
https://vera-office.local
```
Kein Port nötig! ✅

**iPad (im gleichen Netzwerk):**
1. Safari öffnen
2. `https://vera-office.local` eingeben (KEIN Port!)
3. Certificate Warning akzeptieren (einmalig)
4. Login

---

## Service Management (für später)

**Service stoppen:**
```powershell
sc.exe stop CaddyVERA
```

**Service neu starten:**
```powershell
sc.exe stop CaddyVERA
sc.exe start CaddyVERA
```

**Service löschen:**
```powershell
sc.exe stop CaddyVERA
sc.exe delete CaddyVERA
```

**Logs anzeigen:**
Caddy schreibt Logs in Konsole → **Kein Log-File ohne extra Config!**

Für Logs: `caddy.exe run --config Caddyfile` manuell in Admin-PowerShell starten.

---

## Automatischer Start nach Reboot

Service ist auf `start= auto` gesetzt → **startet automatisch nach Windows-Neustart!** ✅

---

## Troubleshooting

**Port 443 schon belegt?**
```powershell
netstat -ano | findstr ":443 "
```
Wenn andere Software Port 443 nutzt → Service kann nicht starten!

**Backend läuft nicht?**
Caddy proxyt zu `localhost:8080` → Backend MUSS laufen!
```powershell
Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing
```

**mDNS advertised falschen Port?**
Update `backend/core/mdns.py`:
```python
await mdns_service.register(port=443, service_name="vera-office")
```

---

## Vorteile Standard-Ports

✅ **User-Friendly:** `vera-office.local` statt `vera-office.local:8443`  
✅ **Session bleibt:** Kein Port-Wechsel → Token bleibt in LocalStorage  
✅ **Professional:** HTTPS ohne Port-Suffix  
✅ **iPad-Kompatibel:** Kamera-API funktioniert (HTTPS erforderlich)  

---

**Status:** Caddyfile ist angepasst (Port 443/80), Service muss noch installiert werden (braucht Admin)!
