# VERA Office - Trusted HTTPS Certificate Setup (mkcert)
# MUST BE RUN AS ADMINISTRATOR!
#
# What this script does:
# 1. Installs local Root-CA (Browser trusts mkcert certificates automatically)
# 2. Creates certificates for 192.168.178.44 + localhost
# 3. Updates vite.config.ts to use the new certificates
# 4. Instructions for restarting Vite dev server

Write-Host "=== VERA Office - Trusted Certificate Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again." -ForegroundColor Yellow
    exit 1
}

# 1. Check if mkcert is downloaded
$mkcertPath = "C:\Jarvix\vera-office\mkcert.exe"
if (-not (Test-Path $mkcertPath)) {
    Write-Host "[1/5] Downloading mkcert..." -ForegroundColor Yellow
    $mkcertUrl = "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-amd64.exe"
    try {
        Invoke-WebRequest -Uri $mkcertUrl -OutFile $mkcertPath -UseBasicParsing
        Write-Host "   ✓ Downloaded to: $mkcertPath" -ForegroundColor Green
    } catch {
        Write-Host "   ✗ Download failed: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/5] mkcert already downloaded" -ForegroundColor Green
}

# 2. Install Root-CA (requires Admin!)
Write-Host "[2/5] Installing local Root-CA (requires Admin)..." -ForegroundColor Yellow
Write-Host "   This creates a trusted certificate authority on your PC." -ForegroundColor Gray
Write-Host "   Browsers will automatically trust certificates created by mkcert." -ForegroundColor Gray
try {
    & $mkcertPath -install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Root-CA installed! Browsers will now trust local certificates." -ForegroundColor Green
    } else {
        Write-Host "   ✗ Root-CA installation failed (Admin rights?)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ✗ Root-CA installation failed: $_" -ForegroundColor Red
    exit 1
}

# 3. Create cert directory
$certDir = "C:\Jarvix\vera-office\frontend\cert"
if (-not (Test-Path $certDir)) {
    Write-Host "[3/5] Creating cert directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $certDir -Force | Out-Null
    Write-Host "   ✓ Created: $certDir" -ForegroundColor Green
} else {
    Write-Host "[3/5] Cert directory exists" -ForegroundColor Green
}

# 4. Generate Certificates
Write-Host "[4/5] Generating certificates for 192.168.178.44 + localhost..." -ForegroundColor Yellow
Write-Host "   This creates key + cert files trusted by your browser." -ForegroundColor Gray
Push-Location $certDir
try {
    & $mkcertPath 192.168.178.44 localhost 127.0.0.1 ::1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Certificates created!" -ForegroundColor Green
        
        # Find generated files
        $certFiles = Get-ChildItem -Path $certDir -Filter "*.pem" | Where-Object { $_.Name -notlike "*-key.pem" }
        $keyFiles = Get-ChildItem -Path $certDir -Filter "*-key.pem"
        
        if ($certFiles.Count -gt 0 -and $keyFiles.Count -gt 0) {
            Write-Host "   Certificate: $($certFiles[0].Name)" -ForegroundColor Gray
            Write-Host "   Private Key: $($keyFiles[0].Name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ✗ Certificate generation failed" -ForegroundColor Red
        Pop-Location
        exit 1
    }
} catch {
    Write-Host "   ✗ Certificate generation failed: $_" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# 5. Update Vite config
Write-Host "[5/5] Updating Vite config..." -ForegroundColor Yellow
$viteConfigPath = "C:\Jarvix\vera-office\frontend\vite.config.ts"

# Find cert filenames (mkcert creates e.g. "192.168.178.44+3.pem")
$certFiles = Get-ChildItem -Path $certDir -Filter "*.pem" | Where-Object { $_.Name -notlike "*-key.pem" }
$keyFiles = Get-ChildItem -Path $certDir -Filter "*-key.pem"

if ($certFiles.Count -eq 0 -or $keyFiles.Count -eq 0) {
    Write-Host "   ✗ Certificate files not found in $certDir" -ForegroundColor Red
    exit 1
}

$certFile = $certFiles[0].Name
$keyFile = $keyFiles[0].Name

Write-Host "   Certificate: $certFile" -ForegroundColor Gray
Write-Host "   Private Key: $keyFile" -ForegroundColor Gray

# Read current vite.config.ts
if (Test-Path $viteConfigPath) {
    $viteConfig = Get-Content $viteConfigPath -Raw
    
    # New HTTPS block (using path.resolve for proper paths)
    $newHttpsBlock = @"
https: {
      key: fs.readFileSync(path.resolve(__dirname, 'cert/$keyFile')),
      cert: fs.readFileSync(path.resolve(__dirname, 'cert/$certFile'))
    }
"@
    
    # Replace existing HTTPS block (matches PFX or key+cert format)
    if ($viteConfig -match "https:\s*\{[^\}]+\}") {
        $viteConfig = $viteConfig -replace "https:\s*\{[^\}]+\}", $newHttpsBlock
        Write-Host "   ✓ Replaced existing HTTPS config with mkcert certificates" -ForegroundColor Green
        Set-Content -Path $viteConfigPath -Value $viteConfig -Encoding UTF8 -NoNewline
    } else {
        Write-Host "   ⚠ No existing HTTPS block found in vite.config.ts" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Add this to your vite.config.ts server block:" -ForegroundColor Cyan
        Write-Host $newHttpsBlock -ForegroundColor White
        Write-Host ""
    }
} else {
    Write-Host "   ✗ vite.config.ts not found at $viteConfigPath" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== ✓ SETUP COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Restart Vite dev server:" -ForegroundColor White
Write-Host "   cd C:\Jarvix\vera-office\frontend" -ForegroundColor Gray
Write-Host "   npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Open browser:" -ForegroundColor White
Write-Host "   https://192.168.178.44:5173" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Browser should show 'Sicher' (no warning!) 🎉" -ForegroundColor White
Write-Host ""
Write-Host "Camera API, File System API, Scanner API are now ready!" -ForegroundColor Green
Write-Host ""
