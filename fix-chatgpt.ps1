# Fix ChatGPT Access Issues
# This script fixes proxy settings to allow ChatGPT access

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing ChatGPT Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Hysteria2
Write-Host "[1/4] Checking Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  [OK] Hysteria2 is running (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Hysteria2 is NOT running!" -ForegroundColor Yellow
    Write-Host "  [INFO] Starting Hysteria2..." -ForegroundColor Gray
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Cannot find start-hysteria2.ps1" -ForegroundColor Red
    }
}

# Check proxy ports
Write-Host ""
Write-Host "[2/4] Checking proxy ports..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
$port1080 = Get-NetTCPConnection -LocalPort 1080 -State Listen -ErrorAction SilentlyContinue

if ($port8080) {
    Write-Host "  [OK] HTTP proxy port 8080 is listening" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Port 8080 is NOT listening!" -ForegroundColor Yellow
}

if ($port1080) {
    Write-Host "  [OK] SOCKS5 proxy port 1080 is listening" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Port 1080 is NOT listening!" -ForegroundColor Yellow
}

# Configure system proxy with exceptions
Write-Host ""
Write-Host "[3/4] Configuring system proxy with ChatGPT exceptions..." -ForegroundColor Yellow
$internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

# Add ChatGPT domains to proxy bypass
$proxyOverride = "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;*.openai.com;*.chatgpt.com;*.anthropic.com;<local>"

Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value $proxyOverride -ErrorAction SilentlyContinue

Write-Host "  [OK] System proxy configured" -ForegroundColor Green
Write-Host "  [OK] ChatGPT domains added to bypass list" -ForegroundColor Green

# Configure Firefox proxy (if profile exists)
Write-Host ""
Write-Host "[4/4] Configuring Firefox proxy..." -ForegroundColor Yellow

$firefoxProfiles = @(
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"
)

$profilePath = $null
foreach ($path in $firefoxProfiles) {
    if (Test-Path $path) {
        $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        if ($profiles) {
            $defaultProfile = $profiles | Where-Object { $_.Name -match "default" } | Select-Object -First 1
            if (-not $defaultProfile) {
                $defaultProfile = $profiles | Select-Object -First 1
            }
            $profilePath = $defaultProfile.FullName
            break
        }
    }
}

if ($profilePath) {
    $userPrefsPath = Join-Path $profilePath "user.js"
    
    # Read existing prefs
    $userPrefs = @{}
    if (Test-Path $userPrefsPath) {
        Get-Content $userPrefsPath | ForEach-Object {
            if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
                $userPrefs[$matches[1]] = $matches[2]
            }
        }
    }
    
    # Configure proxy with exceptions
    $userPrefs["network.proxy.type"] = "1"
    $userPrefs["network.proxy.http"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.http_port"] = "8080"
    $userPrefs["network.proxy.ssl"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.ssl_port"] = "8080"
    $userPrefs["network.proxy.socks"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.socks_port"] = "1080"
    $userPrefs["network.proxy.socks_version"] = "5"
    $userPrefs["network.proxy.socks_remote_dns"] = "true"
    # Add exceptions for ChatGPT
    $userPrefs["network.proxy.no_proxies_on"] = "`"localhost, 127.0.0.1, *.openai.com, *.chatgpt.com, *.anthropic.com`""
    
    # Write user.js
    $content = @()
    foreach ($key in $userPrefs.Keys | Sort-Object) {
        $value = $userPrefs[$key]
        $content += "user_pref(`"$key`", $value);"
    }
    
    Set-Content -Path $userPrefsPath -Value $content -Encoding UTF8
    Write-Host "  [OK] Firefox proxy configured with ChatGPT exceptions" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Firefox profile not found (will configure manually)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "SOLUTIONS FOR CHATGPT:" -ForegroundColor Yellow
Write-Host ""
Write-Host "OPTION 1: Use ChatGPT WITHOUT proxy (Recommended)" -ForegroundColor Cyan
Write-Host "  1. Open Firefox" -ForegroundColor White
Write-Host "  2. Menu (☰) → Settings → Network Settings → Settings..." -ForegroundColor White
Write-Host "  3. In 'No proxy for:' add:" -ForegroundColor White
Write-Host "     *.openai.com, *.chatgpt.com, *.anthropic.com" -ForegroundColor Gray
Write-Host "  4. Click OK and restart Firefox" -ForegroundColor White
Write-Host ""
Write-Host "OPTION 2: Disable proxy temporarily" -ForegroundColor Cyan
Write-Host "  1. Open Firefox" -ForegroundColor White
Write-Host "  2. Menu (☰) → Settings → Network Settings → Settings..." -ForegroundColor White
Write-Host "  3. Select 'No proxy'" -ForegroundColor White
Write-Host "  4. Click OK" -ForegroundColor White
Write-Host "  5. Try accessing ChatGPT" -ForegroundColor White
Write-Host ""
Write-Host "OPTION 3: Use different browser" -ForegroundColor Cyan
Write-Host "  Try Chrome/Edge - they use system proxy settings" -ForegroundColor White
Write-Host ""
Write-Host "TESTING:" -ForegroundColor Yellow
Write-Host "  1. Restart Firefox" -ForegroundColor White
Write-Host "  2. Visit: https://chat.openai.com" -ForegroundColor White
Write-Host "  3. If still blocked, try Option 1 or 2 above" -ForegroundColor White
Write-Host ""

pause


