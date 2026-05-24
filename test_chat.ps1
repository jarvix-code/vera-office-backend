# VERA Chat API Test
$ErrorActionPreference = "Stop"

Write-Host "Getting JWT token..." -ForegroundColor Cyan
$loginBody = @{
    username = "boris"
    password = "vera2024!"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "https://127.0.0.1:8081/api/auth/login" `
    -Method POST `
    -Body $loginBody `
    -ContentType "application/json" `
    -SkipCertificateCheck

$token = $loginResponse.access_token
Write-Host "Token received: $($token.Substring(0,20))..." -ForegroundColor Green

Write-Host ""
Write-Host "Sending chat message..." -ForegroundColor Cyan
$chatBody = @{
    message = "Hallo VERA! Wie geht es dir?"
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $token"
}

$chatResponse = Invoke-RestMethod -Uri "https://127.0.0.1:8081/api/chat" `
    -Method POST `
    -Headers $headers `
    -Body $chatBody `
    -ContentType "application/json" `
    -SkipCertificateCheck `
    -TimeoutSec 60

Write-Host ""
Write-Host "VERA Response:" -ForegroundColor Green
Write-Host $chatResponse.response -ForegroundColor White
Write-Host ""
Write-Host "Tokens used: $($chatResponse.tokens)" -ForegroundColor Gray
Write-Host "Processing time: $($chatResponse.processing_time_ms)ms" -ForegroundColor Gray
