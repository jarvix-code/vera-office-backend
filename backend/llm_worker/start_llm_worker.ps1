# VERA LLM Worker - Windows Startup Script
# Starts Mistral 7B backend on port 18793

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting VERA LLM Worker..." -ForegroundColor Green

# Check if model exists
$modelPath = "C:\Jarvix\vera-office\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf"
if (-not (Test-Path $modelPath)) {
    Write-Host "❌ Model not found: $modelPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Model found: $modelPath" -ForegroundColor Green

# Check if port 18793 is already in use
$portInUse = Get-NetTCPConnection -LocalPort 18793 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Host "⚠️  Port 18793 already in use. LLM Worker may already be running." -ForegroundColor Yellow
    Write-Host "   Use: Stop-Process -Name python -Force (to stop)" -ForegroundColor Yellow
    exit 1
}

# Navigate to llm_worker directory
Set-Location "C:\Jarvix\vera-office\backend\llm_worker"

Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
py -3.11 -m pip install --quiet llama-cpp-python fastapi uvicorn pydantic loguru

Write-Host "🔥 Starting LLM Worker on port 18793..." -ForegroundColor Cyan
Write-Host "   Model: Mistral 7B Instruct v0.2" -ForegroundColor Gray
Write-Host "   Context Window: 8192 tokens" -ForegroundColor Gray
Write-Host "   CPU Threads: 8" -ForegroundColor Gray
Write-Host "" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start server (blocks until Ctrl+C)
py -3.11 server.py
