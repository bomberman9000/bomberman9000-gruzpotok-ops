# Start Hysteria2
# Run from config directory or specify path

param()

$configDir = "$env:USERPROFILE\.hysteria2"
$configFile = Join-Path $configDir "config.yaml"
$hysteria2Exe = "C:\Program Files\hysteria2\hysteria2.exe"

# Check if Hysteria2 exists
if (-not (Test-Path $hysteria2Exe)) {
    $hysteria2Cmd = Get-Command hysteria2 -ErrorAction SilentlyContinue
    if ($hysteria2Cmd) {
        $hysteria2Exe = $hysteria2Cmd.Source
    } else {
        Write-Host "ERROR: Hysteria2 not found!" -ForegroundColor Red
        Write-Host "Run setup-hysteria2.ps1 first" -ForegroundColor Yellow
        exit 1
    }
}

# Check if config exists
if (-not (Test-Path $configFile)) {
    Write-Host "ERROR: Config file not found: $configFile" -ForegroundColor Red
    Write-Host "Run setup-hysteria2.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Check if already running
$existing = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Hysteria2 is already running (PID: $($existing.Id))" -ForegroundColor Yellow
    Write-Host "Stopping existing process..." -ForegroundColor Yellow
    Stop-Process -Name "hysteria2" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Start Hysteria2
Write-Host "Starting Hysteria2..." -ForegroundColor Green
Write-Host "Config: $configFile" -ForegroundColor Gray

Start-Process -FilePath $hysteria2Exe -ArgumentList "-c", $configFile -WindowStyle Hidden

Start-Sleep -Seconds 2

$process = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "Hysteria2 started successfully! PID: $($process.Id)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Proxy configured:" -ForegroundColor Cyan
    Write-Host "  HTTP: 127.0.0.1:8080" -ForegroundColor White
    Write-Host "  SOCKS5: 127.0.0.1:1080" -ForegroundColor White
    Write-Host ""
    Write-Host "Microsoft Store should work now!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Hysteria2 failed to start" -ForegroundColor Red
    Write-Host "Check the config file: $configFile" -ForegroundColor Yellow
}

