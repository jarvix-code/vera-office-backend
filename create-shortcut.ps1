# VERA Office Desktop Shortcut Creator

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "VERA Office.lnk"
$TargetPath = Join-Path $PSScriptRoot "START.bat"
$IconPath = Join-Path $PSScriptRoot "vera-icon.ico"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "VERA Office - Dokumenten-Agent starten"

# Icon setzen (falls vorhanden)
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}

$Shortcut.Save()

Write-Host "[OK] Desktop-Verknüpfung erstellt: $ShortcutPath" -ForegroundColor Green
