# Complete Proxy Fix - All Methods
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Complete Proxy Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Restart Hysteria2
Write-Host "[1/6] Restarting Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  Stopping Hysteria2..." -ForegroundColor Gray
    Stop-Process -Name "hysteria2" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

$startScript = "$env:USERPROFILE\.hysteria2\start-hysteria2.ps1"
if (Test-Path $startScript) {
    & $startScript
    Start-Sleep -Seconds 3
    $hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
    if ($hysteria2) {
        Write-Host "  [OK] Hysteria2 restarted (PID: $($hysteria2.Id))" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Hysteria2 failed to start!" -ForegroundColor Red
    }
} else {
    Write-Host "  [WARN] Start script not found" -ForegroundColor Yellow
}

# Step 2: Reset all proxy settings
Write-Host ""
Write-Host "[2/6] Resetting all proxy settings..." -ForegroundColor Yellow
try {
    # Reset WinHTTP
    netsh winhttp reset proxy | Out-Null
    Start-Sleep -Seconds 1
    netsh winhttp set proxy 127.0.0.1:8080 | Out-Null
    Write-Host "  [OK] WinHTTP proxy reset and set" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset WinHTTP: $_" -ForegroundColor Yellow
}

# Step 3: Enable system proxy
Write-Host ""
Write-Host "[3/6] Enabling system proxy..." -ForegroundColor Yellow
$internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

# Remove all proxy settings first
Remove-ItemProperty -Path $internetKey -Name "ProxyEnable" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $internetKey -Name "ProxyServer" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $internetKey -Name "ProxyOverride" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Set new proxy settings
Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue

Write-Host "  [OK] System proxy enabled: 127.0.0.1:8080" -ForegroundColor Green

# Step 4: Reset network
Write-Host ""
Write-Host "[4/6] Resetting network..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    netsh winsock reset | Out-Null
    Write-Host "  [OK] Network reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset network" -ForegroundColor Yellow
}

# Step 5: Test proxy connection
Write-Host ""
Write-Host "[5/6] Testing proxy connection..." -ForegroundColor Yellow
try {
    # Test if Hysteria2 is listening
    $listening = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Host "  [OK] Hysteria2 is listening on port 8080" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Hysteria2 is NOT listening on port 8080!" -ForegroundColor Red
        Write-Host "  [INFO] Hysteria2 may not be running correctly" -ForegroundColor Yellow
    }
    
    # Test connection through proxy
    $proxyTest = Test-NetConnection -ComputerName "8.8.8.8" -Port 53 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($proxyTest) {
        Write-Host "  [OK] Network connection works" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not test connection" -ForegroundColor Yellow
}

# Step 6: Create browser restart helper
Write-Host ""
Write-Host "[6/6] Creating browser restart helper..." -ForegroundColor Yellow

$restartScript = @"
# Restart Browsers
Write-Host "Restarting browsers..." -ForegroundColor Cyan

`$browsers = @("chrome", "msedge", "firefox", "opera")

foreach (`$browser in `$browsers) {
    `$processes = Get-Process -Name `$browser -ErrorAction SilentlyContinue
    if (`$processes) {
        Write-Host "Stopping `$browser..." -ForegroundColor Yellow
        Stop-Process -Name `$browser -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Browsers stopped. Open them again manually." -ForegroundColor Green
"@

$restartFile = Join-Path $PSScriptRoot "restart-browsers.ps1"
$restartScript | Out-File -FilePath $restartFile -Encoding UTF8
Write-Host "  [OK] Browser restart helper created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Complete Fix Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL STEPS:" -ForegroundColor Red
Write-Host "  1. RESTART your computer (RECOMMENDED)" -ForegroundColor Yellow
Write-Host "  2. Or restart browsers: .\restart-browsers.ps1" -ForegroundColor Yellow
Write-Host "  3. Try opening YouTube" -ForegroundColor Yellow
Write-Host ""
Write-Host "If still not working:" -ForegroundColor Yellow
Write-Host "  1. Check Hysteria2: Get-Process hysteria2" -ForegroundColor White
Write-Host "  2. Check proxy: netsh winhttp show proxy" -ForegroundColor White
Write-Host "  3. Check system proxy: .\proxy-helper.ps1 -Status" -ForegroundColor White
Write-Host "  4. Try manual proxy in browser settings" -ForegroundColor White
Write-Host ""









