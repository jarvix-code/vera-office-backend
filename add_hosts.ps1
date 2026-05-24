$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$content = Get-Content $hostsPath -Raw
if ($content -notmatch "vera-office\.local") {
    Add-Content $hostsPath "`n127.0.0.1    vera-office.local"
    Write-Host "vera-office.local hinzugefuegt"
} else {
    Write-Host "vera-office.local bereits vorhanden"
}
