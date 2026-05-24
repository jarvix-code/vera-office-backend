# VERA Office - Complete Sandbox Setup
# Bereitet ALLES vor für Windows Sandbox Testing

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  VERA Sandbox - Complete Setup      "
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# === SCHRITT 1: Windows Sandbox aktivieren ===
Write-Host "[1/5] Prüfe Windows Sandbox..." -ForegroundColor Yellow

$sandboxFeature = Get-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM"
if ($sandboxFeature.State -ne "Enabled") {
    Write-Host "  Windows Sandbox ist NICHT aktiviert" -ForegroundColor Yellow
    Write-Host "  Aktiviere jetzt... (Neustart erforderlich!)" -ForegroundColor Yellow
    
    Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All -NoRestart
    
    Write-Host ""
    Write-Host "✅ Windows Sandbox aktiviert!" -ForegroundColor Green
    Write-Host "⚠️  NEUSTART ERFORDERLICH!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Nach Neustart dieses Skript erneut ausführen!" -ForegroundColor Cyan
    
    $restart = Read-Host "Jetzt neu starten? (j/n)"
    if ($restart -eq "j") {
        Restart-Computer
        exit
    } else {
        Write-Host "Bitte manuell neu starten und dann Skript erneut ausführen!" -ForegroundColor Yellow
        exit
    }
} else {
    Write-Host "  Windows Sandbox bereits aktiviert" -ForegroundColor Green
}

# === SCHRITT 2: Dependencies in python-embed installieren ===
Write-Host "`n[2/5] Prüfe Python Dependencies..." -ForegroundColor Yellow

$pythonEmbed = "C:\Jarvix\vera-office\installer\python-embed"
$paddleOcrPath = "$pythonEmbed\Lib\site-packages\paddleocr"

if (!(Test-Path $paddleOcrPath)) {
    Write-Host "  Dependencies fehlen - installiere jetzt..." -ForegroundColor Yellow
    
    Push-Location "C:\Jarvix\vera-office\installer"
    try {
        .\INSTALL_DEPS.ps1
    } catch {
        Write-Host "  Fehler bei Dependency-Installation: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  Dependencies bereits installiert (paddleocr vorhanden)" -ForegroundColor Green
}

# === SCHRITT 3: Frontend bauen ===
Write-Host "`n[3/5] Prüfe Frontend Build..." -ForegroundColor Yellow

$frontendDist = "C:\Jarvix\vera-office\frontend\dist"
if (!(Test-Path "$frontendDist\index.html")) {
    Write-Host "  Frontend nicht gebaut - baue jetzt..." -ForegroundColor Yellow
    
    Push-Location "C:\Jarvix\vera-office\frontend"
    try {
        npm run build
    } catch {
        Write-Host "  Fehler beim Frontend-Build: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  Frontend bereits gebaut (dist/index.html vorhanden)" -ForegroundColor Green
}

# === SCHRITT 4: Installer kompilieren ===
Write-Host "`n[4/5] Prüfe VERA Installer..." -ForegroundColor Yellow

$installerExe = "C:\VERA-Office-Installer\VERA-Office-Setup-v1.0.0.exe"
if (!(Test-Path $installerExe)) {
    Write-Host "  Installer nicht vorhanden - kompiliere jetzt..." -ForegroundColor Yellow
    Write-Host "  (Das kann 10-30 Minuten dauern wegen 4GB Modell!)" -ForegroundColor Gray
    
    Push-Location "C:\Jarvix\vera-office"
    try {
        .\BUILD_INSTALLER.ps1
    } catch {
        Write-Host "  Fehler beim Installer-Build: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    $installerSize = (Get-Item $installerExe).Length / 1GB
    Write-Host "  Installer vorhanden ($([math]::Round($installerSize, 2)) GB)" -ForegroundColor Green
}

# === SCHRITT 5: Test-Dokumente vorbereiten ===
Write-Host "`n[5/5] Prüfe Test-Dokumente..." -ForegroundColor Yellow

$testDocsDir = "C:\Jarvix\vera-office\test-documents"
if (!(Test-Path $testDocsDir)) {
    New-Item -ItemType Directory -Path $testDocsDir -Force | Out-Null
    Write-Host "  Test-Dokumente-Ordner erstellt: $testDocsDir" -ForegroundColor Green
    Write-Host "  Bitte Test-PDFs (Rechnungen, Verträge) hier ablegen!" -ForegroundColor Yellow
} else {
    $testDocs = Get-ChildItem $testDocsDir -Filter "*.pdf"
    Write-Host "  Test-Dokumente vorhanden: $($testDocs.Count) PDFs" -ForegroundColor Green
}

# === FERTIG ===
Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "  VERA Sandbox - Setup COMPLETE!     " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Nächste Schritte:" -ForegroundColor Cyan
Write-Host "  1. Doppelklick: VERA-Sandbox.wsb"
Write-Host "  2. Sandbox startet → VERA installiert sich"
Write-Host "  3. VERA starten → Test-PDFs hochladen"
Write-Host "  4. OCR + KI-Klassifikation testen"
Write-Host "  5. Sandbox schließen = alles weg"
Write-Host ""
Write-Host "Test-Dokumente: $testDocsDir" -ForegroundColor Gray
Write-Host "Installer: $installerExe" -ForegroundColor Gray
