# VERA Chat API Test - Simple Version using curl
Write-Host "Getting JWT token..."
$loginResp = curl.exe -k -s -X POST "https://127.0.0.1:8081/api/auth/login" -H "Content-Type: application/json" -d '{\"username\":\"boris\",\"password\":\"vera2024!\"}'
$token = ($loginResp | ConvertFrom-Json).access_token

if ($token) {
    Write-Host "Token OK: $($token.Substring(0,20))...`n"
    
    Write-Host "Sending chat message to VERA..."
    $chatResp = curl.exe -k -X POST "https://127.0.0.1:8081/api/chat" `
        -H "Authorization: Bearer $token" `
        -H "Content-Type: application/json" `
        -d '{\"message\":\"Hallo VERA! Wie geht es dir?\"}' 2>&1
    
    $data = ($chatResp | Out-String | ConvertFrom-Json)
    
    Write-Host "`nVERA Response:"
    Write-Host $data.response -ForegroundColor Green
    Write-Host "`nTokens: $($data.tokens), Time: $($data.processing_time_ms)ms"
} else {
    Write-Host "Login failed!" -ForegroundColor Red
}
