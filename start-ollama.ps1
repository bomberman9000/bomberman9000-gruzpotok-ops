# Start Ollama
# Quick start script

Write-Host "Starting Ollama..." -ForegroundColor Cyan
Write-Host ""

# Check if already running
$existing = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[OK] Ollama is already running!" -ForegroundColor Green
    Write-Host "  PID: $($existing.Id)" -ForegroundColor Gray
    Write-Host "  Started: $($existing.StartTime)" -ForegroundColor Gray
    exit 0
}

# Find Ollama
$ollamaExe = "C:\Users\Shata\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        $ollamaExe = $ollamaCmd.Source
    } else {
        Write-Host "[ERROR] Ollama not found!" -ForegroundColor Red
        exit 1
    }
}

# Start Ollama
Write-Host "Starting Ollama..." -ForegroundColor Yellow
$ollamaDir = Split-Path $ollamaExe -Parent
Push-Location $ollamaDir
Start-Process -FilePath $ollamaExe -WindowStyle Hidden
Pop-Location

Start-Sleep -Seconds 3

# Verify
$process = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "[OK] Ollama started successfully!" -ForegroundColor Green
    Write-Host "  PID: $($process.Id)" -ForegroundColor Gray
    
    # Test connection
    Start-Sleep -Seconds 2
    $test = ollama list 2>&1
    if ($LASTEXITCODE -eq 0 -or $test -match "NAME" -or $test -match "models") {
        Write-Host "[OK] Ollama is responding!" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Ollama is starting, wait a few seconds..." -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Ollama may not have started" -ForegroundColor Yellow
}

Write-Host ""








