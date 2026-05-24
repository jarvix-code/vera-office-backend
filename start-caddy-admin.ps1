# Start Caddy – HTTPS auf Port 8443 (kein Admin nötig)
# iPad-URL: https://192.168.178.44:8443
$ErrorActionPreference = "Stop"

$caddyfile = "C:\Jarvix\vera-office\Caddyfile"

# Caddy-Binary: lokal zuerst, dann PATH
$caddyPath = "C:\Jarvix\vera-office\caddy\caddy.exe"
if (-not (Test-Path $caddyPath)) {
    $caddyPath = (Get-Command caddy -ErrorAction SilentlyContinue)?.Source
}
if (-not $caddyPath) {
    Write-Host "[FEHLER] caddy.exe nicht gefunden!" -ForegroundColor Red
    exit 1
}

Write-Host "Stoppe laufende Caddy-Instanz..." -ForegroundColor Yellow
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1

Write-Host "Starte Caddy HTTPS (Port 8443)..." -ForegroundColor Green
Write-Host "  Binary:    $caddyPath"
Write-Host "  Config:    $caddyfile"
Write-Host "  iPad-URL:  https://192.168.178.44:8443"

Start-Process $caddyPath `
    -ArgumentList "run", "--config", $caddyfile `
    -WorkingDirectory "C:\Jarvix\vera-office" `
    -WindowStyle Minimized

Start-Sleep 2

$port = (Get-NetTCPConnection -LocalPort 8443 -State Listen -ErrorAction SilentlyContinue)
if ($port) {
    Write-Host "Caddy laeuft auf Port 8443!" -ForegroundColor Green
} else {
    Write-Host "Port 8443 nicht offen – Caddy-Log pruefen:" -ForegroundColor Red
    Write-Host "  C:\Jarvix\vera-office\logs\caddy-access.log"
}
