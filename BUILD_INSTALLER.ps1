# VERA Office - Full Installer Build Script
# Automatisiert: Frontend Build → Dependencies Install → Inno Setup Compile

$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$frontendDir = Join-Path $projectRoot "frontend"
$installerDir = Join-Path $projectRoot "installer"
$innoSetupPath = "C:\Program Files (x86)\Inno Setup 6\iscc.exe"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  VERA Office Installer Build        "
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# === SCHRITT 1: Frontend Build ===
Write-Host "[1/4] Frontend Build..." -ForegroundColor Yellow

if (!(Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "  ERROR: frontend/package.json nicht gefunden!" -ForegroundColor Red
    exit 1
}

Push-Location $frontendDir
try {
    Write-Host "  npm run build (das kann 1-2 Minuten dauern)..." -ForegroundColor Gray
    npm run build 2>&1 | Out-Null
    
    if (Test-Path (Join-Path $frontendDir "dist\index.html")) {
        $distSize = (Get-ChildItem (Join-Path $frontendDir "dist") -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "  Frontend Build erfolgreich ($([math]::Round($distSize, 2)) MB)" -ForegroundColor Green
    } else {
        throw "dist/index.html nicht gefunden nach Build"
    }
} catch {
    Write-Host "  ERROR: Frontend Build fehlgeschlagen: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# === SCHRITT 2: Dependencies Check ===
Write-Host "`n[2/4] Dependencies prüfen..." -ForegroundColor Yellow

$pythonEmbed = Join-Path $installerDir "python-embed\python.exe"
if (!(Test-Path $pythonEmbed)) {
    Write-Host "  ERROR: python-embed/python.exe nicht gefunden!" -ForegroundColor Red
    Write-Host "  Bitte python-embed/ Ordner entpacken." -ForegroundColor Yellow
    exit 1
}

$sitePackages = Join-Path $installerDir "python-embed\Lib\site-packages"
if (!(Test-Path (Join-Path $sitePackages "paddleocr"))) {
    Write-Host "  Dependencies fehlen - installiere jetzt..." -ForegroundColor Yellow
    
    Push-Location $installerDir
    try {
        & .\INSTALL_DEPS.ps1
    } catch {
        Write-Host "  ERROR: Dependency-Installation fehlgeschlagen: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  Dependencies bereits installiert" -ForegroundColor Green
}

# === SCHRITT 3: Public Key Check ===
Write-Host "`n[3/4] Public Key prüfen..." -ForegroundColor Yellow

$publicKey = Join-Path $projectRoot "keys\public.pem"
if (!(Test-Path $publicKey)) {
    Write-Host "  WARNING: keys/public.pem nicht gefunden!" -ForegroundColor Yellow
    Write-Host "  Installer wird ohne Lizenz-Verifikation kompiliert." -ForegroundColor Yellow
    Write-Host "  Für Production: Public Key von vera-admin/keys/ kopieren."
} else {
    Write-Host "  Public Key vorhanden" -ForegroundColor Green
}

# === SCHRITT 4: Inno Setup Compile ===
Write-Host "`n[4/4] Inno Setup Compile..." -ForegroundColor Yellow

if (!(Test-Path $innoSetupPath)) {
    Write-Host "  ERROR: Inno Setup nicht gefunden: $innoSetupPath" -ForegroundColor Red
    Write-Host "  Bitte Inno Setup 6 installieren von https://jrsoftware.org/isdl.php"
    exit 1
}

$issFile = Join-Path $installerDir "vera-setup.iss"
if (!(Test-Path $issFile)) {
    Write-Host "  ERROR: vera-setup.iss nicht gefunden!" -ForegroundColor Red
    exit 1
}

try {
    Write-Host "  Kompiliere Installer (das kann 10-30 Minuten dauern wegen Models)..." -ForegroundColor Gray
    & $innoSetupPath $issFile
    
    if ($LASTEXITCODE -eq 0) {
        $outputDir = "D:\VERA-Office-Installer"
        $installerExe = Get-ChildItem $outputDir -Filter "VERA-Office-Setup-*.exe" | Select-Object -First 1
        
        if ($installerExe) {
            $sizeGB = $installerExe.Length / 1GB
            Write-Host "`n=====================================" -ForegroundColor Green
            Write-Host "  Installer Build ERFOLGREICH!        " -ForegroundColor Green
            Write-Host "=====================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Installer: $($installerExe.FullName)" -ForegroundColor Cyan
            Write-Host "Größe: $([math]::Round($sizeGB, 2)) GB" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Nächste Schritte:" -ForegroundColor Yellow
            Write-Host "  1. Installer auf USB-Stick kopieren"
            Write-Host "  2. Auf frischer Windows-VM testen"
            Write-Host "  3. Beim Kunden installieren"
        } else {
            throw "Installer-EXE nicht gefunden in $outputDir"
        }
    } else {
        throw "Inno Setup Compile fehlgeschlagen (Exit Code: $LASTEXITCODE)"
    }
    
} catch {
    Write-Host "`nERROR: Installer-Kompilierung fehlgeschlagen: $_" -ForegroundColor Red
    Write-Host "`nTroubleshooting:" -ForegroundColor Yellow
    Write-Host "  - Prüfe Inno Setup Log"
    Write-Host "  - Prüfe Pfade in vera-setup.iss"
    Write-Host "  - Prüfe ob alle Source-Dateien existieren"
    exit 1
}
