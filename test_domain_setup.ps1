# VERA Office - Domain Setup Test Script
# Prüft ob vera-office.local korrekt konfiguriert ist

Write-Host "`n=== VERA Office Domain Setup Test ===" -ForegroundColor Cyan
Write-Host "Teste vera-office.local Konfiguration...`n" -ForegroundColor Gray

# Test 1: mDNS Resolution
Write-Host "[1/5] mDNS Resolution Test (vera-office.local)" -ForegroundColor Yellow
try {
    $result = Test-Connection -ComputerName "vera-office.local" -Count 1 -ErrorAction Stop
    Write-Host "  ✓ vera-office.local kann aufgelöst werden" -ForegroundColor Green
    Write-Host "    IP: $($result.IPV4Address)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ vera-office.local kann NICHT aufgelöst werden" -ForegroundColor Red
    Write-Host "    Mögliche Ursache: Bonjour Service fehlt" -ForegroundColor Gray
    Write-Host "    Fix: iTunes installieren oder Bonjour Service manuell" -ForegroundColor Gray
}

# Test 2: Caddy Running
Write-Host "`n[2/5] Caddy Service Check" -ForegroundColor Yellow
$caddyProcess = Get-Process -Name "caddy" -ErrorAction SilentlyContinue
if ($caddyProcess) {
    Write-Host "  ✓ Caddy läuft (PID: $($caddyProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  ✗ Caddy läuft NICHT" -ForegroundColor Red
    Write-Host "    Fix: caddy run --config Caddyfile" -ForegroundColor Gray
}

# Test 3: VERA Backend Running
Write-Host "`n[3/5] VERA Backend Check (Port 8080)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 3 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ VERA Backend läuft" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ VERA Backend läuft NICHT" -ForegroundColor Red
    Write-Host "    Fix: python -m backend.main" -ForegroundColor Gray
}

# Test 4: HTTP Redirect (Port 80 → 8443)
Write-Host "`n[4/5] HTTP Redirect Test (Port 80 → 8443)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://vera-office.local" -MaximumRedirection 0 -ErrorAction Stop
} catch {
    if ($_.Exception.Response.StatusCode -eq 301 -or $_.Exception.Response.StatusCode -eq 308) {
        $location = $_.Exception.Response.Headers["Location"]
        if ($location -like "*8443*") {
            Write-Host "  ✓ HTTP Redirect funktioniert" -ForegroundColor Green
            Write-Host "    Redirect: $location" -ForegroundColor Gray
        } else {
            Write-Host "  ✗ Redirect geht nicht zu Port 8443" -ForegroundColor Red
        }
    } else {
        Write-Host "  ✗ Kein Redirect gefunden" -ForegroundColor Red
    }
}

# Test 5: HTTPS Endpoint (Port 8443)
Write-Host "`n[5/5] HTTPS Endpoint Test (Port 8443)" -ForegroundColor Yellow
try {
    # Skip certificate validation for self-signed cert
    add-type @"
        using System.Net;
        using System.Security.Cryptography.X509Certificates;
        public class TrustAllCertsPolicy : ICertificatePolicy {
            public bool CheckValidationResult(
                ServicePoint srvPoint, X509Certificate certificate,
                WebRequest request, int certificateProblem) {
                return true;
            }
        }
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    
    $response = Invoke-WebRequest -Uri "https://vera-office.local:8443/health" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ HTTPS Endpoint erreichbar" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ HTTPS Endpoint NICHT erreichbar" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
}

# Summary
Write-Host "`n=== Zusammenfassung ===" -ForegroundColor Cyan
Write-Host "Erwartetes Verhalten:" -ForegroundColor Gray
Write-Host "  1. User tippt 'vera-office.local' im Browser" -ForegroundColor Gray
Write-Host "  2. Browser löst via mDNS auf (Bonjour)" -ForegroundColor Gray
Write-Host "  3. HTTP Request geht zu Port 80" -ForegroundColor Gray
Write-Host "  4. Caddy redirected zu HTTPS Port 8443" -ForegroundColor Gray
Write-Host "  5. Caddy proxied zu Backend Port 8080" -ForegroundColor Gray
Write-Host "  6. User sieht VERA Office Interface`n" -ForegroundColor Gray

# USB Test Endpoint
Write-Host "=== Bonus: USB Import API Test ===" -ForegroundColor Cyan
try {
    $usbResponse = Invoke-WebRequest -Uri "http://localhost:8080/api/import-usb/scan" -TimeoutSec 3 -ErrorAction Stop
    $usbData = $usbResponse.Content | ConvertFrom-Json
    Write-Host "  ✓ USB Import API erreichbar" -ForegroundColor Green
    Write-Host "    USB Mounted: $($usbData.mounted)" -ForegroundColor Gray
    if ($usbData.mounted) {
        Write-Host "    Path: $($usbData.path)" -ForegroundColor Gray
        Write-Host "    Files: $($usbData.file_count)" -ForegroundColor Gray
        Write-Host "    Folders: $($usbData.folders.Count)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ USB Import API nicht erreichbar" -ForegroundColor Red
}

Write-Host "`nTest abgeschlossen.`n" -ForegroundColor Cyan
