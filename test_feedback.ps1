$boundary = [System.Guid]::NewGuid().ToString()
$bodyLines = @(
    "--$boundary",
    'Content-Disposition: form-data; name="type"',
    '',
    'bug',
    "--$boundary",
    'Content-Disposition: form-data; name="message"',
    '',
    'Test feedback',
    "--$boundary--"
)
$body = $bodyLines -join "`r`n"

Invoke-WebRequest -Uri "http://192.168.178.44:8001/api/feedback/submit" `
    -Method POST `
    -ContentType "multipart/form-data; boundary=$boundary" `
    -Body $body `
    -UseBasicParsing | Select-Object StatusCode, Content
