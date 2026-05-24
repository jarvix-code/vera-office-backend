# ====================================================================
# VERA Office Complete Setup Script
# Run this ONCE as Administrator to complete the installation
# ====================================================================

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "VERA Office Domain Setup" -ForegroundColor Cyan
Write-Host "==================================`n" -ForegroundColor Cyan

# Check if running as Admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click and select 'Run as Administrator'`n" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# 1. Update hosts file
Write-Host "[1/3] Adding vera-office.local to hosts file..." -ForegroundColor Yellow
$hostsFile = "C:\Windows\System32\drivers\etc\hosts"
$hostsEntry = "127.0.0.1 vera-office.local"

try {
    $content = Get-Content $hostsFile
    if ($content -notmatch "vera-office.local") {
        Add-Content -Path $hostsFile -Value "`n$hostsEntry" -Force
        Write-Host "      OK - Entry added" -ForegroundColor Green
    } else {
        Write-Host "      OK - Entry already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "      FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Stop old Caddy
Write-Host "`n[2/3] Stopping old Caddy processes..." -ForegroundColor Yellow
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1
Write-Host "      OK" -ForegroundColor Green

# 3. Start Caddy with correct config
Write-Host "`n[3/3] Starting Caddy..." -ForegroundColor Yellow
$caddyExe = "C:\Jarvix\vera-office\caddy\caddy.exe"
$config = "C:\Jarvix\vera-office\Caddyfile.final"

if (-not (Test-Path $caddyExe)) {
    Write-Host "      ERROR: Caddy not found at $caddyExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $config)) {
    Write-Host "      ERROR: Config not found at $config" -ForegroundColor Red
    exit 1
}

Start-Process -FilePath $caddyExe -ArgumentList "run", "--config", $config, "--adapter", "caddyfile" -WindowStyle Hidden -WorkingDirectory "C:\Jarvix\vera-office"

Start-Sleep 3

# Verify
$caddy = Get-Process caddy -ErrorAction SilentlyContinue
if ($caddy) {
    Write-Host "      OK - Caddy running (PID: $($caddy.Id))" -ForegroundColor Green
} else {
    Write-Host "      ERROR: Caddy failed to start!" -ForegroundColor Red
    exit 1
}

# Show results
Write-Host "`n==================================`n" -ForegroundColor Cyan
Write-Host "VERA Office is now accessible at:" -ForegroundColor Green
Write-Host "  https://vera-office.local:8443" -ForegroundColor White
Write-Host "  https://127.0.0.1:8443" -ForegroundColor Gray
Write-Host "  http://vera-office.local (auto-redirect)" -ForegroundColor Gray
Write-Host "  http://127.0.0.1:8001 (auto-redirect)" -ForegroundColor Gray
Write-Host "`nNote: Browser will show SSL warning (self-signed cert)." -ForegroundColor Yellow
Write-Host "      Click 'Advanced' → 'Proceed anyway' to continue.`n" -ForegroundColor Yellow
Write-Host "Setup complete!" -ForegroundColor Green

Read-Host "`nPress Enter to close"
