# Test Proxy Connection
# No admin required

Write-Host "Testing proxy connection..." -ForegroundColor Cyan
Write-Host ""

# Check Hysteria2
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "[OK] Hysteria2 is running (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Hysteria2 is NOT running!" -ForegroundColor Red
    Write-Host "Start it: .\start-hysteria2.ps1" -ForegroundColor Yellow
    exit 1
}

# Check ports
Write-Host ""
Write-Host "Checking ports..." -ForegroundColor Cyan
$port8080 = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
$port1080 = Get-NetTCPConnection -LocalPort 1080 -State Listen -ErrorAction SilentlyContinue

if ($port8080) {
    Write-Host "[OK] Port 8080 (HTTP) is listening" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Port 8080 is NOT listening!" -ForegroundColor Red
    Write-Host "Hysteria2 may not be configured correctly" -ForegroundColor Yellow
}

if ($port1080) {
    Write-Host "[OK] Port 1080 (SOCKS5) is listening" -ForegroundColor Green
} else {
    Write-Host "[WARN] Port 1080 is NOT listening" -ForegroundColor Yellow
}

# Check proxy settings
Write-Host ""
Write-Host "Checking proxy settings..." -ForegroundColor Cyan
$proxy = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
if ($proxy.ProxyEnable -eq 1) {
    Write-Host "[OK] System proxy is enabled: $($proxy.ProxyServer)" -ForegroundColor Green
} else {
    Write-Host "[FAIL] System proxy is DISABLED!" -ForegroundColor Red
    Write-Host "Enable it: .\enable-proxy.ps1" -ForegroundColor Yellow
}

# Test connection
Write-Host ""
Write-Host "Testing connection..." -ForegroundColor Cyan
try {
    $test = Invoke-WebRequest -Uri "http://www.google.com" -Proxy "http://127.0.0.1:8080" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] Proxy connection works!" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Proxy connection failed: $_" -ForegroundColor Red
    Write-Host "Hysteria2 may not be working correctly" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "If proxy test failed, try:" -ForegroundColor Yellow
Write-Host "  1. Restart Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host "  2. Check config: C:\Users\Shata\.hysteria2\config.yaml" -ForegroundColor White
Write-Host "  3. Restart computer" -ForegroundColor White
Write-Host ""









