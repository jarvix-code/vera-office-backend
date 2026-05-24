<#
.SYNOPSIS
VERA Office Backend Production Startup Script

.DESCRIPTION
Kills old processes, cleans port 8081, starts backend with proper logging

.NOTES
Created: 2026-03-29
Author: Javix (VERA Startup Debug Mission)
#>

Write-Host "=== VERA Office Backend Startup ===" -ForegroundColor Cyan

# === STEP 1: Kill old processes ===
Write-Host "`n[1/6] Stopping old Python processes..." -ForegroundColor Yellow
Get-Process python,py -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -notlike "*VS Code*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 5
Write-Host "✅ Old processes stopped" -ForegroundColor Green

# === STEP 2: Clean port 8081 ===
Write-Host "`n[2/6] Checking port 8081..." -ForegroundColor Yellow
$port = Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue
if ($port) {
    Write-Host "⚠️ Port 8081 occupied by PID $($port.OwningProcess) - killing..." -ForegroundColor Yellow
    Stop-Process -Id $port.OwningProcess -Force
    Start-Sleep -Seconds 5
}
Write-Host "✅ Port 8081 free" -ForegroundColor Green

# === STEP 3: Clean database locks ===
Write-Host "`n[3/6] Cleaning database locks..." -ForegroundColor Yellow
$dataDir = "C:\Jarvix\vera-office\data"
if (Test-Path "$dataDir\vera.db-shm") { Remove-Item "$dataDir\vera.db-shm" -Force }
if (Test-Path "$dataDir\vera.db-wal") { Remove-Item "$dataDir\vera.db-wal" -Force }
if (Test-Path "$dataDir\vera.db-journal") { Remove-Item "$dataDir\vera.db-journal" -Force }
Write-Host "✅ Database locks cleaned" -ForegroundColor Green

# === STEP 4: Create logs directory ===
Write-Host "`n[4/6] Preparing logs directory..." -ForegroundColor Yellow
$logsDir = "C:\Jarvix\vera-office\logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}
Write-Host "✅ Logs directory ready: $logsDir" -ForegroundColor Green

# === STEP 5: Set environment ===
Write-Host "`n[5/6] Setting environment..." -ForegroundColor Yellow
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "C:\Jarvix\vera-office"
Write-Host "✅ Environment configured" -ForegroundColor Green

# === STEP 6: Start backend ===
Write-Host "`n[6/6] Starting VERA Backend..." -ForegroundColor Yellow
cd C:\Jarvix\vera-office

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$errorLog = "$logsDir\error_$timestamp.log"
$outputLog = "$logsDir\output_$timestamp.log"

Start-Process -FilePath "py" `
    -ArgumentList "-3.11", "-m", "backend.main" `
    -WindowStyle Hidden `
    -RedirectStandardError $errorLog `
    -RedirectStandardOutput $outputLog

Write-Host "✅ Backend starting..." -ForegroundColor Green
Write-Host "   Logs: $outputLog" -ForegroundColor Gray
Write-Host "   Errors: $errorLog" -ForegroundColor Gray

# === STEP 7: Wait for startup ===
Write-Host "`n[7/7] Waiting for backend to be ready (30s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# === STEP 8: Verify health ===
Write-Host "`n[8/8] Verifying health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8081/api/auth/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ Health check PASSED: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "`n=== VERA Backend ONLINE ===" -ForegroundColor Cyan
    Write-Host "   Local:  http://127.0.0.1:8081" -ForegroundColor White
    Write-Host "   LAN:    https://192.168.178.44:8081" -ForegroundColor White
    Write-Host "   mDNS:   https://vera-office.local:8443" -ForegroundColor White
    Write-Host "`n✅ All systems operational!" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check FAILED!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n⚠️ Check logs:" -ForegroundColor Yellow
    Write-Host "   $outputLog" -ForegroundColor Gray
    Write-Host "   $errorLog" -ForegroundColor Gray
    exit 1
}
