#!/usr/bin/env pwsh
# VERA Office - Sandbox Starter
# Startet VERA in Docker-Container (sicher, isoliert, mit PowerShell Core)

$ErrorActionPreference = "Stop"
$DockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$DockerComposePath = "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  VERA Office Sandbox Starter        "
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 1. Docker Desktop prüfen
Write-Host "[1/4] Prüfe Docker Desktop..." -ForegroundColor Yellow
$dockerRunning = & $DockerPath ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker Desktop startet..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    # Warte bis Docker verfügbar ist (max 60 Sekunden)
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 3
        $elapsed += 3
        $dockerRunning = & $DockerPath ps 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker Desktop läuft" -ForegroundColor Green
            break
        }
    }
    
    if ($elapsed -ge $timeout) {
        Write-Host "  Docker Desktop Timeout (60s)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Docker Desktop läuft bereits" -ForegroundColor Green
}

# 2. Container Status prüfen
Write-Host "`n[2/4] Prüfe VERA Container..." -ForegroundColor Yellow
$containerStatus = & $DockerPath ps -a --filter "name=vera-backend" --format "{{.Status}}" 2>$null
if ($containerStatus -like "*Up*") {
    Write-Host "  Container läuft bereits" -ForegroundColor Green
} elseif ($containerStatus) {
    Write-Host "  Starte gestoppten Container..." -ForegroundColor Yellow
    & $DockerComposePath -f "docker\docker-compose.yml" start
} else {
    Write-Host "  Baue und starte Container (erstes Mal dauert ~5 Min)..." -ForegroundColor Yellow
    & $DockerComposePath -f "docker\docker-compose.yml" up -d --build
}

# 3. Warte auf Backend
Write-Host "`n[3/4] Warte auf Backend (Health Check)..." -ForegroundColor Yellow
$timeout = 60
$elapsed = 0
while ($elapsed -lt $timeout) {
    Start-Sleep -Seconds 3
    $elapsed += 3
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response) {
            Write-Host "  Backend läuft" -ForegroundColor Green
            break
        }
    } catch {
        # Noch nicht bereit
    }
}

if ($elapsed -ge $timeout) {
    Write-Host "  Backend braucht länger (normal beim ersten Start)" -ForegroundColor Yellow
}

# 4. Status-Übersicht
Write-Host "`n[4/4] Status" -ForegroundColor Yellow
& $DockerPath ps --filter "name=vera-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n=====================================" -ForegroundColor Green
Write-Host "  VERA Sandbox ist bereit!            " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "  1. Sandbox betreten:  docker exec -it vera-backend bash"
Write-Host "  2. PowerShell:        pwsh"
Write-Host "  3. VERA testen:       curl http://localhost:8000/health"
Write-Host "  4. Logs:              docker logs -f vera-backend"
Write-Host ""
Write-Host "Dokumentation: SANDBOX_GUIDE.md" -ForegroundColor Gray
Write-Host "Stoppen:       docker-compose -f docker\docker-compose.yml down" -ForegroundColor Gray
