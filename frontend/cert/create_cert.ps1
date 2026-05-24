# VERA Office - HTTPS Certificate Creator
# RUN AS ADMINISTRATOR!

cd "C:\Jarvix\vera-office\frontend\cert"

Write-Host "Creating Self-Signed Certificate for VERA Office..."

$cert = New-SelfSignedCertificate `
    -DnsName "vera-office.local","192.168.178.44","localhost" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -KeyExportPolicy Exportable `
    -KeySpec Signature `
    -KeyLength 2048 `
    -KeyAlgorithm RSA `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(5)

Write-Host "Certificate Thumbprint: $($cert.Thumbprint)"

# Export PFX
$pfxPassword = ConvertTo-SecureString -String "vera-office-2026" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "vera-office.pfx" -Password $pfxPassword | Out-Null

# Export CER (for Browser import)
Export-Certificate -Cert $cert -FilePath "vera-office.cer" | Out-Null

# Extract PEM for Node.js
$certPem = "-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks') + "`n-----END CERTIFICATE-----"
$certPem | Out-File -Encoding ASCII -FilePath "cert.pem"

# Private Key (via PFX → PEM)
$pfx = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("vera-office.pfx", "vera-office-2026", [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
$keyBytes = $pfx.PrivateKey.ExportPkcs8PrivateKey()
$keyPem = "-----BEGIN PRIVATE KEY-----`n" + [Convert]::ToBase64String($keyBytes, 'InsertLineBreaks') + "`n-----END PRIVATE KEY-----"
$keyPem | Out-File -Encoding ASCII -FilePath "key.pem"

Write-Host "`nFiles created:"
Get-ChildItem -Name

Write-Host "`n=== NEXT STEPS ==="
Write-Host "1. Import vera-office.cer in Browser (Trust as Root CA)"
Write-Host "2. Frontend: npm run dev (uses cert.pem + key.pem)"
Write-Host "3. Open: https://192.168.178.44:8443/capture"
Write-Host "`nHTTPS Certificate ready!"
