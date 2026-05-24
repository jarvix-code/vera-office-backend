#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start VERA Auto-Fix Agent Daemon

.DESCRIPTION
    Startet den Auto-Fix Agent, der:
    - data/bug_queue/ pollt
    - Fix-Briefings erstellt
    - Telegram-Rückkanal bereitstellt

.EXAMPLE
    .\start_autofix.ps1
    .\start_autofix.ps1 -Debug
#>

param(
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Paths
$ProjectRoot = $PSScriptRoot
$ServiceScript = Join-Path $ProjectRoot "backend\services\autofix_agent.py"
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "autofix_agent.log"

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Write-Host "🚀 VERA Auto-Fix Agent" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Check if service script exists
if (-not (Test-Path $ServiceScript)) {
    Write-Host "❌ Service script not found: $ServiceScript" -ForegroundColor Red
    exit 1
}

# Find Python
$Python = $null
$PythonPaths = @(
    "python",
    "python3",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
)

foreach ($PyPath in $PythonPaths) {
    try {
        $Version = & $PyPath --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $Python = $PyPath
            Write-Host "✅ Python found: $Version" -ForegroundColor Green
            break
        }
    } catch {
        continue
    }
}

if (-not $Python) {
    Write-Host "❌ Python not found in PATH or common locations" -ForegroundColor Red
    Write-Host "   Please install Python 3.10+ or add it to PATH" -ForegroundColor Yellow
    exit 1
}

# Check dependencies
Write-Host "🔍 Checking dependencies..." -ForegroundColor Cyan
$RequiredPackages = @("requests", "pyyaml")
$MissingPackages = @()

foreach ($Package in $RequiredPackages) {
    $Check = & $Python -c "import $Package" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $MissingPackages += $Package
    }
}

if ($MissingPackages.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($MissingPackages -join ', ')" -ForegroundColor Yellow
    Write-Host "   Installing..." -ForegroundColor Cyan
    
    & $Python -m pip install $MissingPackages
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ All dependencies installed" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "🎯 Starting Auto-Fix Agent..." -ForegroundColor Cyan
Write-Host "   Script: $ServiceScript" -ForegroundColor DarkGray
Write-Host "   Log: $LogFile" -ForegroundColor DarkGray
Write-Host ""

if ($Debug) {
    Write-Host "🐛 Debug mode — output to console" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    & $Python $ServiceScript
} else {
    Write-Host "📋 Logging to: $LogFile" -ForegroundColor Cyan
    Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    
    # Run with output redirected to log file
    & $Python $ServiceScript *> $LogFile
}

Write-Host ""
Write-Host "🛑 Auto-Fix Agent stopped" -ForegroundColor Yellow
