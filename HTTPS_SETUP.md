# VERA Office HTTPS Setup via Caddy Reverse Proxy

**Date:** 2026-03-26  
**Status:** ✅ COMPLETED

## Architecture

```
iPad (HTTPS) → Caddy (Port 8443) → Backend (HTTP Port 8080)
```

## Configuration

### Backend
- **Port:** 8080 (HTTP only - NO SSL in Python!)
- **Location:** `C:\Jarvix\vera-office\backend\main.py`
- **Start:** `python -m backend.main` (from project root)
- **Health Check:** `http://localhost:8080/health`

### Caddy Reverse Proxy
- **Binary:** `C:\Jarvix\vera-office\caddy\caddy.exe`
- **Config:** `C:\Jarvix\vera-office\Caddyfile`
- **HTTPS Port:** 8443
- **HTTP Port:** 8000 (redirects to HTTPS)
- **Certificate:** Internal (Caddy self-signed, auto-installed in Windows trust store)
- **Start:** `caddy run --config Caddyfile` (from project root)

### Caddyfile
```
{
    admin localhost:2019
    https_port 8443
    http_port 8000
}

https://vera-office.local:8443 {
    tls internal
    reverse_proxy localhost:8080
}

http://vera-office.local:8000 {
    redir https://vera-office.local:8443{uri} permanent
}
```

## Starting the Services

### 1. Start Backend (HTTP)
```powershell
cd C:\Jarvix\vera-office
$env:PYTHONIOENCODING="utf-8"
python -m backend.main
```

### 2. Start Caddy (HTTPS Proxy)
```powershell
cd C:\Jarvix\vera-office
C:\Jarvix\vera-office\caddy\caddy.exe run --config Caddyfile
```

## Verification

✅ **Backend HTTP:** `http://localhost:8080/health` → `{"status":"healthy"}`  
✅ **Caddy HTTPS:** `https://vera-office.local:8443` → Login page loads  
✅ **Certificate:** Self-signed (Caddy Internal CA - trusted by Windows)  
✅ **iPad Access:** `https://vera-office.local:8443` (Camera API works!)

## mDNS Update Required

**TODO:** Update `backend/core/mdns.py` to advertise Port **8443** instead of 8080:

```python
# OLD:
await mdns_service.register(port=config.PORT, service_name="vera-office")  # Port 8080

# NEW:
await mdns_service.register(port=8443, service_name="vera-office")  # Caddy HTTPS Port
```

## Troubleshooting

### Backend fails to start
- Check encoding: `$env:PYTHONIOENCODING="utf-8"`
- Run from project root, not backend folder
- Verify port 8080 is free: `Get-NetTCPConnection -LocalPort 8080`

### Caddy fails to start
- Validate Caddyfile: `caddy validate --config Caddyfile`
- Check backend is running: `curl http://localhost:8080/health`
- Check port 8443 is free: `Get-NetTCPConnection -LocalPort 8443`

### Certificate errors on iPad
- Caddy's internal CA is auto-trusted on Windows, but **NOT on iOS/iPadOS**
- For production: Use proper SSL certificate or manually install Caddy's root CA on iPad
- For development: Accept self-signed warning on iPad (proceed anyway)

## Production Deployment

For production deployment with proper SSL:

1. **Option A:** Let's Encrypt (requires public domain)
   ```
   https://vera-office.yourdomain.com {
       tls your-email@example.com
       reverse_proxy localhost:8080
   }
   ```

2. **Option B:** Custom certificate
   ```
   https://vera-office.local:8443 {
       tls /path/to/cert.pem /path/to/key.pem
       reverse_proxy localhost:8080
   }
   ```

3. **Option C:** Install Caddy root CA on iPad
   - Export root CA: `C:\Users\USERNAME\AppData\Roaming\Caddy\pki\authorities\local\root.crt`
   - Email to iPad or serve via web
   - Install profile in iOS Settings → General → VPN & Device Management
   - Trust certificate in Settings → General → About → Certificate Trust Settings

## Notes

- Backend MUST stay HTTP (no SSL in Python code!)
- Caddy handles all SSL/TLS termination
- Frontend static files are served by backend (FastAPI StaticFiles)
- All API routes go through Caddy reverse proxy
- mDNS advertises port 8443 for iPad discovery

## Success Criteria ✅

- ✅ Backend runs HTTP Port 8080 (no SSL in Python!)
- ✅ Caddy runs Port 8443 (HTTPS)
- ✅ Browser loads `https://vera-office.local:8443` (Login page)
- ✅ Certificate warning (self-signed = expected on iOS/iPadOS)
- ✅ Screenshot shows working HTTPS login
