# Fix hosts file for vera-office.local
$hostsFile = "C:\Windows\System32\drivers\etc\hosts"
$entry = "127.0.0.1 vera-office.local"

$content = Get-Content $hostsFile
if ($content -notmatch "vera-office.local") {
    Add-Content -Path $hostsFile -Value "`n$entry"
    Write-Host "✅ Added vera-office.local to hosts file"
} else {
    Write-Host "✅ vera-office.local already in hosts file"
}
