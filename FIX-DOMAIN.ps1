# VERA Office Domain Fix Script
$ErrorActionPreference = "Stop"

Write-Host "`n=== VERA Office Domain Fix ===" -ForegroundColor Cyan

# 1. Fix hosts file
Write-Host "`n[1/4] Fixing hosts file..." -ForegroundColor Yellow
$hostsFile = "C:\Windows\System32\drivers\etc\hosts"
$hostsEntry = "127.0.0.1 vera-office.local"

try {
    $content = Get-Content $hostsFile -ErrorAction Stop
    if ($content -notmatch "vera-office.local") {
        Add-Content -Path $hostsFile -Value "`n$hostsEntry" -Force
        Write-Host "  ✓ Added vera-office.local" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Already exists" -ForegroundColor Green
    }
} catch {
    Write-Host "  ! Need admin rights!" -ForegroundColor Red
    Write-Host "  Run as admin: .\FIX-DOMAIN.ps1" -ForegroundColor Yellow
    exit 1
}

# 2. Stop old Caddy
Write-Host "`n[2/4] Stopping old Caddy..." -ForegroundColor Yellow
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 1
Write-Host "  ✓ Stopped" -ForegroundColor Green

# 3. Clean Caddy data
Write-Host "`n[3/4] Cleaning SSL data..." -ForegroundColor Yellow
$caddyDataDir = "$env:LOCALAPPDATA\Caddy"
if (Test-Path $caddyDataDir) {
    Remove-Item -Path $caddyDataDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  ✓ Removed old certificates" -ForegroundColor Green
}

# 4. Start Caddy
Write-Host "`n[4/4] Starting Caddy..." -ForegroundColor Yellow

$caddyExe = "C:\Jarvix\vera-office\caddy\caddy.exe"
$caddyfile = "C:\Jarvix\vera-office\Caddyfile"
$workDir = "C:\Jarvix\vera-office"

# Test Port 80 availability
$canBindPort80 = $false
try {
    $testSocket = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, 80)
    $testSocket.Start()
    $testSocket.Stop()
    $canBindPort80 = $true
} catch {
    Write-Host "  ! Port 80 blocked, using fallback config" -ForegroundColor Yellow
}

if (!$canBindPort80) {
    $caddyfile = "C:\Jarvix\vera-office\Caddyfile.fallback"
}

# Start Caddy
$proc = Start-Process $caddyExe -ArgumentList "run", "--config", $caddyfile -WorkingDirectory $workDir -PassThru -WindowStyle Hidden
Start-Sleep 3

# Verify
if (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ Caddy started (PID: $($proc.Id))" -ForegroundColor Green
    
    Write-Host "`n=== Access VERA ===" -ForegroundColor Cyan
    Write-Host "https://vera-office.local:8443" -ForegroundColor White
    if ($canBindPort80) {
        Write-Host "http://vera-office.local (auto-redirect)" -ForegroundColor White
    } else {
        Write-Host "http://vera-office.local:8000 (auto-redirect)" -ForegroundColor White
    }
    
    Write-Host "`n✓ DONE!" -ForegroundColor Green
} else {
    Write-Host "  X Caddy failed to start!" -ForegroundColor Red
    exit 1
}
