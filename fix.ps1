Write-Host 'VERA Domain Fix (No Admin)' -ForegroundColor Cyan
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host 'Caddy stopped' -ForegroundColor Green
$caddyData = "$env:LOCALAPPDATA\Caddy"
if (Test-Path $caddyData) { Remove-Item -Path $caddyData -Recurse -Force }
Write-Host 'SSL cleaned' -ForegroundColor Green
$caddy = 'C:\Jarvix\vera-office\caddy\caddy.exe'
$config = 'C:\Jarvix\vera-office\Caddyfile.fallback'
Start-Process $caddy -ArgumentList 'run --config $config' -WorkingDirectory 'C:\Jarvix\vera-office' -WindowStyle Hidden
Start-Sleep 2
Write-Host 'Caddy started' -ForegroundColor Green
Write-Host 'Access: https://vera-office.local:8443' -ForegroundColor Cyan
