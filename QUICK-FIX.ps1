# Quick Fix - Run as ADMIN!

Write-Host "VERA Domain Quick Fix" -ForegroundColor Cyan

# 1. Add hosts entry
$hostsFile = "C:\Windows\System32\drivers\etc\hosts"
$entry = "127.0.0.1 vera-office.local"
Add-Content -Path $hostsFile -Value "`n$entry" -Force -ErrorAction SilentlyContinue
Write-Host "✓ hosts file updated" -ForegroundColor Green

# 2. Stop old Caddy
Get-Process caddy -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "✓ Old Caddy stopped" -ForegroundColor Green

# 3. Clean SSL
$caddyData = "$env:LOCALAPPDATA\Caddy"
if (Test-Path $caddyData) {
    Remove-Item -Path $caddyData -Recurse -Force
}
Write-Host "✓ SSL data cleaned" -ForegroundColor Green

# 4. Start Caddy (with Port 80)
$caddy = "C:\Jarvix\vera-office\caddy\caddy.exe"
$config = "C:\Jarvix\vera-office\Caddyfile"
Start-Process $caddy -ArgumentList "run --config $config" -WorkingDirectory "C:\Jarvix\vera-office" -WindowStyle Hidden
Start-Sleep 2
Write-Host "✓ Caddy started" -ForegroundColor Green

Write-Host "`nAccess: https://vera-office.local:8443" -ForegroundColor White
