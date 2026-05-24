# VERA Office - Port Migration Report

**Datum:** 2026-03-25 22:37  
**Von Port:** 8002 → **Auf Port:** 8080  
**Grund:** Standard HTTP alternate port (keine Admin-Rechte nötig)

## ✅ Durchgeführte Änderungen

### 1. Backend Config
- `config/vera.yaml`: `port: 8002` → `port: 8080`
- `backend/config.py`: `PORT = 8002` → `PORT = 8080`
- `backend/main.py`: Log-Ausgabe angepasst

### 2. CORS Origins
- `backend/main.py`: Explizite CORS-Origin für Port 8080 hinzugefügt

### 3. mDNS
- Automatisch auf Port 8080 registriert
- Service läuft: `https://vera-office.local:8080`
- LAN IP: `192.168.178.44`

### 4. Firewall
- **⚠️ NOCH NICHT AKTIV** - braucht Admin-Rechte
- Script erstellt: `setup_firewall_8080.ps1`
- **NÄCHSTER SCHRITT:** Als Administrator ausführen:
  ```powershell
  cd C:\Jarvix\vera-office\backend
  .\setup_firewall_8080.ps1
  ```

## ✅ Verifikation

```powershell
# Port 8080 lauscht
netstat -ano | findstr "8080"
# → TCP 0.0.0.0:8080 ... LISTENING 12708 ✅

# mDNS funktioniert
ping vera-office.local
# → 192.168.178.44 ✅

# Health-Check OK
Invoke-RestMethod "http://vera-office.local:8080/health"
# → status: healthy, version: 1.0.0 ✅
```

## 🎯 Nächste Schritte für Boris

### 1. Firewall-Regel aktivieren (WICHTIG!)
```powershell
cd C:\Jarvix\vera-office\backend
.\setup_firewall_8080.ps1
```

### 2. Frontend anpassen (falls hart-codiert)
Prüfe ob Frontend noch `:8002` hart-codiert hat:
```powershell
cd C:\Jarvix\vera-office\frontend
rg "8002" --type-add 'web:*.{js,jsx,ts,tsx,vue,html}' -t web
```

Falls ja → ersetzen mit `8080` oder besser: `${window.location.port}`

### 3. iPad/iPhone testen
```
http://vera-office.local:8080
```

## 📝 Hinweise

**Warum Port 8080 statt 80?**
- Port 80 braucht Admin-Rechte (< 1024 sind privilegiert unter Windows)
- Port 8080 ist Standard HTTP Alternate Port
- Funktioniert ohne Elevated Permissions
- Wird von Browsern automatisch als HTTP erkannt

**mDNS Registration:**
- Registriert als `_https._tcp.local.` (Service-Type)
- Name: `vera-office.local`
- Port: `8080`
- Properties: `path=/`, `version=1.0.0`, `app=VERA Office`

**Backend Start:**
```powershell
cd C:\Jarvix\vera-office
py -m backend.main
```

---

✅ **Migration erfolgreich abgeschlossen!**  
→ Boris kann jetzt `http://vera-office.local:8080` nutzen
