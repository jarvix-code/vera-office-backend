#!/usr/bin/env pwsh
# VERA Office - One-Click Starter

$ErrorActionPreference = "Stop"
$DockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$DockerComposePath = "C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"

Write-Host "VERA Office Starter" -ForegroundColor Cyan
Write-Host "==================`n"

# 1. Docker Desktop pruefen
Write-Host "[1/4] Pruefe Docker Desktop..." -ForegroundColor Yellow
$dockerRunning = & $DockerPath ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker Desktop startet..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    # Warte bis Docker verfuegbar ist (max 60 Sekunden)
    $timeout = 60
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        Start-Sleep -Seconds 3
        $elapsed += 3
        $dockerRunning = & $DockerPath ps 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker Desktop laeuft" -ForegroundColor Green
            break
        }
    }
    
    if ($elapsed -ge $timeout) {
        Write-Host "  Docker Desktop Timeout (60s)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Docker Desktop laeuft bereits" -ForegroundColor Green
}

# 2. Container Status pruefen
Write-Host "`n[2/4] Pruefe VERA Container..." -ForegroundColor Yellow
$containerStatus = & $DockerPath ps -a --filter "name=vera-backend" --format "{{.Status}}" 2>$null
if ($containerStatus -like "*Up*") {
    Write-Host "  Container laeuft bereits" -ForegroundColor Green
} elseif ($containerStatus) {
    Write-Host "  Starte gestoppten Container..." -ForegroundColor Yellow
    & $DockerComposePath -f "docker\docker-compose.yml" start
} else {
    Write-Host "  Baue und starte Container (erstes Mal dauert ~2 Min)..." -ForegroundColor Yellow
    & $DockerComposePath -f "docker\docker-compose.yml" up -d --build
}

# 3. Warte auf Backend
Write-Host "`n[3/4] Warte auf Backend (Health Check)..." -ForegroundColor Yellow
$timeout = 30
$elapsed = 0
while ($elapsed -lt $timeout) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response) {
            Write-Host "  Backend laeuft" -ForegroundColor Green
            break
        }
    } catch {
        # Noch nicht bereit
    }
}

if ($elapsed -ge $timeout) {
    Write-Host "  Backend braucht laenger (normal beim ersten Start)" -ForegroundColor Yellow
}

# 4. Status-Uebersicht
Write-Host "`n[4/4] Status" -ForegroundColor Yellow
& $DockerPath ps --filter "name=vera-backend" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n==> VERA Office ist bereit!" -ForegroundColor Green
Write-Host "`nNaechste Schritte:"
Write-Host "  - Sandbox betreten:  docker exec -it vera-backend bash"
Write-Host "  - PowerShell:        pwsh"
Write-Host "  - API testen:        curl http://localhost:8000/health"
Write-Host "  - Logs:              docker logs -f vera-backend"
Write-Host "  - Stoppen:           docker-compose -f docker\docker-compose.yml down"
