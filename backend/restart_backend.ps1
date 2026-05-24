# VERA Backend Restart Script
# Stops existing backend and starts with new changes

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "VERA Backend Restart" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Stop existing backend
Write-Host "`n[1/3] Stopping existing backend processes..." -ForegroundColor Yellow

$processes = Get-Process | Where-Object { $_.ProcessName -eq "python" }
foreach ($proc in $processes) {
    try {
        $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        if ($cmdline -like "*main.py*" -or $cmdline -like "*uvicorn*vera*") {
            Write-Host "  Stopping process $($proc.Id)..." -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force
            Write-Host "  ✅ Stopped" -ForegroundColor Green
        }
    }
    catch {
        # Ignore errors
    }
}

Start-Sleep -Seconds 2

# Check if port is free
Write-Host "`n[2/3] Checking port 8081..." -ForegroundColor Yellow
$portCheck = netstat -ano | findstr ":8081"
if ($portCheck) {
    Write-Host "  ⚠️  Port 8081 still in use!" -ForegroundColor Yellow
    Write-Host "  $portCheck" -ForegroundColor Gray
}
else {
    Write-Host "  ✅ Port 8081 is free" -ForegroundColor Green
}

# Start backend
Write-Host "`n[3/3] Starting backend with new changes..." -ForegroundColor Yellow
Write-Host "  Working directory: C:\Jarvix\vera-office\backend" -ForegroundColor Gray
Write-Host "  Command: python main.py" -ForegroundColor Gray
Write-Host "`n  Note: Backend will start in this window. Press Ctrl+C to stop." -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Cyan

cd C:\Jarvix\vera-office\backend
python main.py
