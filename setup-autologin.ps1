# VERA Office — Windows Auto-Login Setup
# Setzt Registry-Keys fuer automatisches Login ohne Passwort-Eingabe
# MUSS als Administrator ausgefuehrt werden!
#
# Nutzung:
#   .\setup-autologin.ps1 -Username "Praxis" -Password "vera123"
#   .\setup-autologin.ps1 -Disable   # Auto-Login deaktivieren

param(
    [string]$Username,
    [string]$Password,
    [switch]$Disable
)

$RegPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "FEHLER: Dieses Script muss als Administrator ausgefuehrt werden!" -ForegroundColor Red
    Write-Host "Rechtsklick > Als Administrator ausfuehren" -ForegroundColor Yellow
    exit 1
}

if ($Disable) {
    Write-Host "Auto-Login wird deaktiviert..." -ForegroundColor Yellow
    Set-ItemProperty -Path $RegPath -Name "AutoAdminLogon" -Value "0"
    Remove-ItemProperty -Path $RegPath -Name "DefaultPassword" -ErrorAction SilentlyContinue
    Write-Host "Auto-Login deaktiviert." -ForegroundColor Green
    exit 0
}

if (-not $Username) {
    $Username = Read-Host "Windows-Benutzername"
}
if (-not $Password) {
    $Password = Read-Host "Windows-Passwort" -AsSecureString
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
    )
}

Write-Host "Konfiguriere Auto-Login fuer Benutzer '$Username'..." -ForegroundColor Cyan

Set-ItemProperty -Path $RegPath -Name "AutoAdminLogon" -Value "1"
Set-ItemProperty -Path $RegPath -Name "DefaultUserName" -Value $Username
Set-ItemProperty -Path $RegPath -Name "DefaultPassword" -Value $Password
Set-ItemProperty -Path $RegPath -Name "DefaultDomainName" -Value $env:COMPUTERNAME

Write-Host ""
Write-Host "Auto-Login aktiviert!" -ForegroundColor Green
Write-Host "Beim naechsten Neustart wird '$Username' automatisch angemeldet." -ForegroundColor Green
Write-Host ""
Write-Host "HINWEIS: Das Passwort wird im Klartext in der Registry gespeichert." -ForegroundColor Yellow
Write-Host "Zum Deaktivieren: .\setup-autologin.ps1 -Disable" -ForegroundColor Yellow
