# Launch Steam with Proxy
# This script ensures VPN is running and launches Steam with proxy settings

Write-Host "Запуск Steam с VPN..." -ForegroundColor Cyan
Write-Host ""

# Check Hysteria2
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (-not $hysteria2) {
    Write-Host "Запускаю Hysteria2..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    }
}

# Set environment variables
$env:HTTP_PROXY = "http://127.0.0.1:8080"
$env:HTTPS_PROXY = "http://127.0.0.1:8080"
$env:http_proxy = "http://127.0.0.1:8080"
$env:https_proxy = "http://127.0.0.1:8080"
$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"

# Find Steam executable
$steamPaths = @(
    "$env:ProgramFiles(x86)\Steam\steam.exe",
    "$env:ProgramFiles\Steam\steam.exe",
    "$env:LOCALAPPDATA\Programs\Steam\steam.exe"
)

$steamExe = $null
foreach ($path in $steamPaths) {
    if (Test-Path $path) {
        $steamExe = $path
        break
    }
}

# If not found, try to find via process
if (-not $steamExe) {
    $steamProcess = Get-Process -Name "Steam" -ErrorAction SilentlyContinue
    if ($steamProcess) {
        $steamExe = $steamProcess.Path
    }
}

if ($steamExe) {
    Write-Host "Запускаю Steam: $steamExe" -ForegroundColor Green
    Start-Process -FilePath $steamExe
    Write-Host "Steam запущен с VPN!" -ForegroundColor Green
} else {
    Write-Host "Steam не найден. Запустите Steam вручную." -ForegroundColor Yellow
    Write-Host "Steam будет использовать системный прокси автоматически." -ForegroundColor Gray
}
