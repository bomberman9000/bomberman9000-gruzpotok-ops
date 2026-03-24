# Fix Firefox Proxy Settings for Hysteria2
# This script configures Firefox to use Hysteria2 proxy

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Firefox Proxy for Hysteria2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Hysteria2 proxy settings
$proxyHost = "127.0.0.1"
$proxyPort = "8080"
$socksPort = "1080"

Write-Host "[INFO] Hysteria2 Proxy:" -ForegroundColor Yellow
Write-Host "  HTTP: $proxyHost`:$proxyPort" -ForegroundColor Gray
Write-Host "  SOCKS5: $proxyHost`:$socksPort" -ForegroundColor Gray
Write-Host ""

# Check if Firefox is running
$firefoxProcess = Get-Process -Name "firefox" -ErrorAction SilentlyContinue
if ($firefoxProcess) {
    Write-Host "[WARN] Firefox is running. Please close it first!" -ForegroundColor Yellow
    Write-Host "Press any key after closing Firefox..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Find Firefox profile directory
$firefoxProfiles = @(
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"
)

$profilePath = $null
foreach ($path in $firefoxProfiles) {
    if (Test-Path $path) {
        $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        if ($profiles) {
            # Use the default profile or the first one
            $defaultProfile = $profiles | Where-Object { $_.Name -match "default" } | Select-Object -First 1
            if (-not $defaultProfile) {
                $defaultProfile = $profiles | Select-Object -First 1
            }
            $profilePath = $defaultProfile.FullName
            break
        }
    }
}

if (-not $profilePath) {
    Write-Host "[ERROR] Firefox profile not found!" -ForegroundColor Red
    Write-Host "Please start Firefox at least once to create a profile." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[OK] Found Firefox profile: $profilePath" -ForegroundColor Green
Write-Host ""

# Path to prefs.js
$prefsPath = Join-Path $profilePath "prefs.js"
$userPrefsPath = Join-Path $profilePath "user.js"

# Create user.js if it doesn't exist
if (-not (Test-Path $userPrefsPath)) {
    New-Item -Path $userPrefsPath -ItemType File -Force | Out-Null
}

Write-Host "[INFO] Configuring proxy settings..." -ForegroundColor Yellow

# Read existing user.js
$userPrefs = @{}
if (Test-Path $userPrefsPath) {
    Get-Content $userPrefsPath | ForEach-Object {
        if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
            $userPrefs[$matches[1]] = $matches[2]
        }
    }
}

# Set proxy preferences
$userPrefs["network.proxy.type"] = "1"  # Manual proxy
$userPrefs["network.proxy.http"] = "`"$proxyHost`""
$userPrefs["network.proxy.http_port"] = "$proxyPort"
$userPrefs["network.proxy.ssl"] = "`"$proxyHost`""
$userPrefs["network.proxy.ssl_port"] = "$proxyPort"
$userPrefs["network.proxy.socks"] = "`"$proxyHost`""
$userPrefs["network.proxy.socks_port"] = "$socksPort"
$userPrefs["network.proxy.socks_version"] = "5"
$userPrefs["network.proxy.socks_remote_dns"] = "true"
# Add exceptions for ChatGPT and other OpenAI services
$userPrefs["network.proxy.no_proxies_on"] = "`"localhost, 127.0.0.1, *.openai.com, *.chatgpt.com, *.anthropic.com`""

# Write user.js
$content = @()
foreach ($key in $userPrefs.Keys | Sort-Object) {
    $value = $userPrefs[$key]
    $content += "user_pref(`"$key`", $value);"
}

Set-Content -Path $userPrefsPath -Value $content -Encoding UTF8

Write-Host "[OK] Proxy settings configured!" -ForegroundColor Green
Write-Host ""

# Also try to set via about:config (requires Firefox to be closed)
Write-Host "[INFO] Proxy settings:" -ForegroundColor Cyan
Write-Host "  Type: Manual" -ForegroundColor Gray
Write-Host "  HTTP Proxy: $proxyHost`:$proxyPort" -ForegroundColor Gray
Write-Host "  SSL Proxy: $proxyHost`:$proxyPort" -ForegroundColor Gray
Write-Host "  SOCKS5 Proxy: $proxyHost`:$socksPort" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Make sure Hysteria2 is running:" -ForegroundColor White
Write-Host "   .\start-hysteria2.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Start Firefox" -ForegroundColor White
Write-Host ""
Write-Host "3. Verify proxy:" -ForegroundColor White
Write-Host "   - Open: about:preferences#general" -ForegroundColor Gray
Write-Host "   - Scroll to Network Settings" -ForegroundColor Gray
Write-Host "   - Click Settings" -ForegroundColor Gray
Write-Host "   - Should show: Manual proxy configuration" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Test connection:" -ForegroundColor White
Write-Host "   - Visit: https://whatismyipaddress.com" -ForegroundColor Gray
Write-Host "   - Should show your VPN IP" -ForegroundColor Gray
Write-Host ""

# Alternative: Manual instructions
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "MANUAL CONFIGURATION (if needed):" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open Firefox" -ForegroundColor White
Write-Host "2. Menu (☰) → Settings" -ForegroundColor White
Write-Host "3. Scroll to 'Network Settings'" -ForegroundColor White
Write-Host "4. Click 'Settings...'" -ForegroundColor White
Write-Host "5. Select 'Manual proxy configuration'" -ForegroundColor White
Write-Host "6. Set:" -ForegroundColor White
Write-Host "   HTTP Proxy: $proxyHost Port: $proxyPort" -ForegroundColor Gray
Write-Host "   SSL Proxy: $proxyHost Port: $proxyPort" -ForegroundColor Gray
Write-Host "   SOCKS Host: $proxyHost Port: $socksPort" -ForegroundColor Gray
Write-Host "   SOCKS v5" -ForegroundColor Gray
Write-Host "   ✓ Proxy DNS when using SOCKS v5" -ForegroundColor Gray
Write-Host "7. Click OK" -ForegroundColor White
Write-Host ""

pause


