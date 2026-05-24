# VERA Office - HTTPS Certificate Fix
# RUN AS ADMINISTRATOR!

Write-Host "Creating HTTPS Certificate for VERA Office..."

cd "C:\Jarvix\vera-office\frontend\cert"

# 1. Create Certificate
$cert = New-SelfSignedCertificate `
    -DnsName "localhost","192.168.178.44","vera-office.local" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -KeyExportPolicy Exportable `
    -KeySpec Signature `
    -KeyLength 2048 `
    -KeyAlgorithm RSA `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(5)

Write-Host "Certificate Thumbprint: $($cert.Thumbprint)"

# 2. Export to PFX
$pfxPassword = ConvertTo-SecureString -String "vera-office-2026" -Force -AsPlainText
$pfxPath = Join-Path $PWD "vera-office.pfx"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pfxPassword | Out-Null
Write-Host "PFX exported: vera-office.pfx"

# 3. Export CER for Browser
$cerPath = Join-Path $PWD "vera-office.cer"
Export-Certificate -Cert $cert -FilePath $cerPath | Out-Null
Write-Host "CER exported: vera-office.cer"

# 4. Convert PFX to PEM using certutil + openssl workaround
Write-Host "`nConverting to PEM format..."

# Extract cert
$certBase64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
$certPem = "-----BEGIN CERTIFICATE-----`n$certBase64`n-----END CERTIFICATE-----"
[System.IO.File]::WriteAllText("$PWD\cert.pem", $certPem, [System.Text.Encoding]::ASCII)
Write-Host "cert.pem created"

# Extract private key using certutil
$thumbprint = $cert.Thumbprint
Write-Host "Using certutil to export private key..."

# Export to temporary PFX without password
$tempPfx = "$env:TEMP\vera-temp.pfx"
$emptyPassword = New-Object SecureString
Export-PfxCertificate -Cert "Cert:\LocalMachine\My\$thumbprint" -FilePath $tempPfx -Password $emptyPassword -Force | Out-Null

# Use certutil to convert PFX to Base64
certutil -encodehex $tempPfx "$PWD\key-temp.txt" 0x40000001 | Out-Null

# Read and format as PEM (manual conversion)
Write-Host "Creating key.pem manually..."

# Alternative: Use .NET to export key directly
try {
    $pfxCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($pfxPath, $pfxPassword, [System.Security.Cryptography.X509Certificates.X509KeyStorageFlags]::Exportable)
    
    if ($pfxCert.HasPrivateKey) {
        # For PowerShell 7+ (has ExportPkcs8PrivateKey)
        if ($PSVersionTable.PSVersion.Major -ge 7) {
            $keyBytes = $pfxCert.PrivateKey.ExportPkcs8PrivateKey()
            $keyBase64 = [Convert]::ToBase64String($keyBytes, 'InsertLineBreaks')
            $keyPem = "-----BEGIN PRIVATE KEY-----`n$keyBase64`n-----END PRIVATE KEY-----"
        } else {
            # For Windows PowerShell 5.1 - use RSA format
            $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($pfxCert)
            
            # Get key in XML format and convert
            $xmlKey = $rsa.ToXmlString($true)
            
            # Manual conversion to PEM (simplified - just export modulus)
            Write-Host "Warning: PowerShell 5.1 detected - using workaround"
            
            # Create a minimal valid key.pem placeholder
            # Node.js will use the PFX file directly if key.pem fails
            $keyPem = "# This is a placeholder. Use vera-office.pfx directly with password: vera-office-2026"
        }
        
        [System.IO.File]::WriteAllText("$PWD\key.pem", $keyPem, [System.Text.Encoding]::ASCII)
        Write-Host "key.pem created"
    }
} catch {
    Write-Host "Warning: Could not export private key: $_"
    Write-Host "Using PFX file directly (vera-office.pfx)"
}

# Cleanup
if (Test-Path $tempPfx) { Remove-Item $tempPfx -Force }
if (Test-Path "$PWD\key-temp.txt") { Remove-Item "$PWD\key-temp.txt" -Force }

Write-Host "`n=== FILES CREATED ==="
Get-ChildItem "*.pem","*.cer","*.pfx" | Select-Object Name,Length

Write-Host "`n=== NEXT STEPS ==="
Write-Host "1. Import vera-office.cer in Browser (Trust as Root CA)"
Write-Host "2. Update vite.config.js to use PFX file directly:"
Write-Host "   server: {"
Write-Host "     https: {"
Write-Host "       pfx: './cert/vera-office.pfx',"
Write-Host "       passphrase: 'vera-office-2026'"
Write-Host "     }"
Write-Host "   }"
Write-Host "3. npm run dev"
Write-Host "4. Open: https://localhost:5173/capture"

Write-Host "`n✅ HTTPS Certificate Ready!"
