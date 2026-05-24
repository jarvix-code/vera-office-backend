# VERA Chat Fix - Test Script
# Tests all endpoints to verify the fix

$ErrorActionPreference = "Continue"
$backend = "http://127.0.0.1:8080"  # VERA Backend port
$llm_worker = "http://127.0.0.1:18793"  # LLM Worker port

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "VERA Chat Fix - Test Sequence" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Test 1: LLM Worker Direct
Write-Host "`n[1/5] Testing LLM Worker Direct..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$llm_worker/chat" -Method Post `
        -ContentType "application/json" `
        -Body '{"message":"Hallo","max_tokens":128}' `
        -TimeoutSec 30
    
    Write-Host "  ✅ LLM Worker Response:" -ForegroundColor Green
    Write-Host "     $($response.response)" -ForegroundColor White
}
catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Backend Health Check
Write-Host "`n[2/5] Testing Backend Health Check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backend/api/chat/health" -Method Get
    
    Write-Host "  ✅ Health Status:" -ForegroundColor Green
    Write-Host "     Backend: $($response.backend)" -ForegroundColor White
    Write-Host "     LLM Worker: $($response.llm_worker)" -ForegroundColor White
    
    if ($response.llm_details) {
        Write-Host "     Details: $($response.llm_details | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Backend Test Endpoint (No Auth)
Write-Host "`n[3/5] Testing Backend Test Endpoint (No Auth)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backend/api/chat/test?message=Test" -Method Post
    
    if ($response.error) {
        Write-Host "  ❌ ERROR:" -ForegroundColor Red
        Write-Host "     $($response | ConvertTo-Json)" -ForegroundColor Gray
    }
    else {
        Write-Host "  ✅ Test Response:" -ForegroundColor Green
        Write-Host "     $($response.response)" -ForegroundColor White
    }
}
catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Full Backend Health
Write-Host "`n[4/5] Testing Full Backend Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$backend/health" -Method Get
    
    Write-Host "  ✅ Backend Status: $($response.status)" -ForegroundColor Green
}
catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: LLM Worker Health
Write-Host "`n[5/5] Testing LLM Worker Health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$llm_worker/health" -Method Get
    
    Write-Host "  ✅ LLM Worker Status:" -ForegroundColor Green
    Write-Host "     $($response | ConvertTo-Json -Compress)" -ForegroundColor White
}
catch {
    Write-Host "  ❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "Test Sequence Complete" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

Write-Host "`nNEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. If all tests passed: Test via Frontend (Gwen)" -ForegroundColor White
Write-Host "  2. If Test #1 failed: LLM Worker not running" -ForegroundColor White
Write-Host "  3. If Test #2-3 failed but #1 passed: Backend connection issue" -ForegroundColor White
Write-Host "  4. Check logs: backend\logs\vera.log" -ForegroundColor White
