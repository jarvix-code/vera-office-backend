#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test VERA Auto-Fix Pipeline

.DESCRIPTION
    Erstellt einen Test-Bug und prüft ob die Pipeline funktioniert
#>

$ErrorActionPreference = "Stop"

Write-Host "🧪 VERA Auto-Fix Pipeline — Test" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$ProjectRoot = $PSScriptRoot
$QueueDir = Join-Path $ProjectRoot "data\bug_queue"
$FixTasksDir = Join-Path $QueueDir "fix_tasks"
$InProgressDir = Join-Path $QueueDir "in_progress"

# Ensure directories exist
@($QueueDir, $FixTasksDir, $InProgressDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
    }
}

# Create test bug
$TestBug = @{
    version = 1
    ticket_id = 9999
    timestamp = (Get-Date -Format "o")
    status = "pending"
    original_text = "TEST BUG: OCR erkennt keine Umlaute bei deutschen Rechnungen"
    user = @{
        id = 123456
        username = "test_user"
        name = "Test User"
    }
    analysis = @{
        module = "ocr"
        severity = "high"
        title = "OCR Umlaut-Erkennung fehlerhaft"
        description = "Umlaute werden nicht erkannt"
        expected = "ä, ö, ü sollten erkannt werden"
        possible_cause = "Tesseract language config falsch"
        affected_files = @(
            "backend/core/ocr_engine.py",
            "backend/core/image_processor.py"
        )
        reproduction_steps = @(
            "Deutsche Rechnung scannen",
            "OCR-Ergebnis prüfen",
            "Umlaute fehlen"
        )
        fix_hint = "Prüfe Tesseract language config (deu.traineddata)"
        analysis_method = "test"
    }
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BugFile = Join-Path $QueueDir "bug_9999_$Timestamp.json"

Write-Host "📝 Creating test bug: $($BugFile | Split-Path -Leaf)" -ForegroundColor Cyan
$TestBug | ConvertTo-Json -Depth 10 | Out-File -FilePath $BugFile -Encoding UTF8

Write-Host "✅ Test bug created" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Start Auto-Fix Agent: .\start_autofix.ps1 -Debug" -ForegroundColor White
Write-Host "   2. Wait max. 30 seconds" -ForegroundColor White
Write-Host "   3. Check fix_tasks/: ls data\bug_queue\fix_tasks\" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Expected result:" -ForegroundColor Cyan
Write-Host "   - bug_9999_*.json moved to in_progress/" -ForegroundColor White
Write-Host "   - fix_task_9999_*.json created in fix_tasks/" -ForegroundColor White
Write-Host "   - fix_task contains code context from affected files" -ForegroundColor White
Write-Host ""

# Wait for user
Write-Host "Press any key to check status..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
Write-Host ""

# Check results
Write-Host "🔍 Checking results..." -ForegroundColor Cyan

$FixTasks = Get-ChildItem -Path $FixTasksDir -Filter "fix_task_9999_*.json" -ErrorAction SilentlyContinue
$InProgress = Get-ChildItem -Path $InProgressDir -Filter "bug_9999_*.json" -ErrorAction SilentlyContinue

if ($FixTasks) {
    Write-Host "✅ Fix task created: $($FixTasks[0].Name)" -ForegroundColor Green
    
    $FixTaskContent = Get-Content $FixTasks[0].FullName -Raw | ConvertFrom-Json
    Write-Host ""
    Write-Host "📊 Fix Task Summary:" -ForegroundColor Cyan
    Write-Host "   Ticket ID: $($FixTaskContent.ticket_id)" -ForegroundColor White
    Write-Host "   Module: $($FixTaskContent.fix_instructions.module)" -ForegroundColor White
    Write-Host "   Severity: $($FixTaskContent.fix_instructions.severity)" -ForegroundColor White
    Write-Host "   Code files loaded: $($FixTaskContent.code_context.Count)" -ForegroundColor White
    
    $FixTaskContent.code_context | ForEach-Object {
        $Status = if ($_.exists) { "✅" } else { "❌" }
        $Truncated = if ($_.truncated) { " (truncated)" } else { "" }
        Write-Host "      $Status $($_.path) — $($_.lines) lines$Truncated" -ForegroundColor DarkGray
    }
} else {
    Write-Host "⚠️  No fix task found yet" -ForegroundColor Yellow
    Write-Host "   Make sure Auto-Fix Agent is running!" -ForegroundColor Yellow
}

if ($InProgress) {
    Write-Host "✅ Bug moved to in_progress: $($InProgress[0].Name)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Bug not moved to in_progress yet" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🧹 Cleanup:" -ForegroundColor Cyan
Write-Host "   Remove test files? (y/n)" -ForegroundColor Yellow
$Cleanup = Read-Host

if ($Cleanup -eq 'y') {
    if ($FixTasks) { Remove-Item $FixTasks[0].FullName -Force }
    if ($InProgress) { Remove-Item $InProgress[0].FullName -Force }
    if (Test-Path $BugFile) { Remove-Item $BugFile -Force }
    Write-Host "✅ Test files removed" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Test files kept for inspection" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ Test complete!" -ForegroundColor Green
