# No-Admin Fix (uses Port 8000 instead of 80)

Write-Host "VERA Domain Fix (No Admin)" -ForegroundColor Cyan

# 1. Stop old Caddy
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "✓ Old Caddy stopped" -ForegroundColor Green

# 2. Clean SSL (user-level only)
$caddyData = "$env:LOCALAPPDATA\Caddy"
if (Test-Path $caddyData) {
    Remove-Item -Path $caddyData -Recurse -Force
}
Write-Host "✓ SSL data cleaned" -ForegroundColor Green

# 3. Start Caddy with fallback config (Port 8000)
$caddy = "C:\Jarvix\vera-office\caddy\caddy.exe"
$config = "C:\Jarvix\vera-office\Caddyfile.fallback"
Start-Process $caddy -ArgumentList "run --config $config" -WorkingDirectory "C:\Jarvix\vera-office" -WindowStyle Hidden
Start-Sleep 2
Write-Host "✓ Caddy started" -ForegroundColor Green

Write-Host "`nAccess VERA:" -ForegroundColor White
Write-Host "  https://vera-office.local:8443" -ForegroundColor Cyan
Write-Host "  http://vera-office.local:8000 (redirects to HTTPS)" -ForegroundColor Cyan
Write-Host "  https://127.0.0.1:8443 (fallback)" -ForegroundColor Gray
Write-Host "`nNote: Add 127.0.0.1 vera-office.local to hosts file manually if needed" -ForegroundColor Yellow
