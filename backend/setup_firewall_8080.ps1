# VERA Office - Firewall Regel für Port 8080 erstellen
# MUSS ALS ADMINISTRATOR ausgeführt werden!

Write-Host "Erstelle Firewall-Regel für VERA Office Port 8080..." -ForegroundColor Cyan

try {
    New-NetFirewallRule `
        -DisplayName "VERA Office HTTP 8080" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 8080 `
        -Action Allow `
        -Profile Any `
        -ErrorAction Stop
    
    Write-Host "✅ Firewall-Regel erstellt: Port 8080 ist jetzt erreichbar" -ForegroundColor Green
    
    # Prüfe ob Regel existiert
    $rule = Get-NetFirewallRule -DisplayName "VERA Office HTTP 8080" -ErrorAction SilentlyContinue
    if ($rule) {
        Write-Host "✅ Regel verifiziert" -ForegroundColor Green
    }
    
} catch {
    Write-Host "❌ Fehler beim Erstellen der Firewall-Regel: $_" -ForegroundColor Red
    Write-Host "Stelle sicher, dass du dieses Script als Administrator ausführst!" -ForegroundColor Yellow
    exit 1
}
