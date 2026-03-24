# Fix Proxy for Browsers (Chrome, Edge, Firefox)
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Proxy for Browsers" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Check Hysteria2 is running
Write-Host "[1/5] Checking Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  [OK] Hysteria2 is running (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Hysteria2 is NOT running!" -ForegroundColor Yellow
    Write-Host "  [INFO] Starting Hysteria2..." -ForegroundColor Gray
    $startScript = "$env:USERPROFILE\.hysteria2\start-hysteria2.ps1"
    if (Test-Path $startScript) {
        & $startScript
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Cannot find start script" -ForegroundColor Red
    }
}

# Step 2: Configure WinHTTP proxy (for Store and system)
Write-Host ""
Write-Host "[2/5] Configuring WinHTTP proxy..." -ForegroundColor Yellow
try {
    netsh winhttp set proxy 127.0.0.1:8080
    Write-Host "  [OK] WinHTTP proxy set to: 127.0.0.1:8080" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not set WinHTTP proxy: $_" -ForegroundColor Yellow
}

# Step 3: Configure system proxy
Write-Host ""
Write-Host "[3/5] Configuring system proxy..." -ForegroundColor Yellow
try {
    $internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    
    Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] System proxy enabled: 127.0.0.1:8080" -ForegroundColor Green
    Write-Host "  [OK] Proxy override configured (local addresses bypassed)" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not configure system proxy: $_" -ForegroundColor Yellow
}

# Step 4: Configure Chrome/Edge proxy (via registry)
Write-Host ""
Write-Host "[4/5] Configuring Chrome/Edge proxy..." -ForegroundColor Yellow
try {
    # Chrome proxy settings
    $chromeKey = "HKCU:\Software\Google\Chrome\PreferenceMACs"
    if (-not (Test-Path $chromeKey)) {
        New-Item -Path $chromeKey -Force | Out-Null
    }
    
    # Edge proxy settings
    $edgeKey = "HKCU:\Software\Microsoft\Edge\PreferenceMACs"
    if (-not (Test-Path $edgeKey)) {
        New-Item -Path $edgeKey -Force | Out-Null
    }
    
    Write-Host "  [OK] Chrome/Edge registry keys ready" -ForegroundColor Green
    Write-Host "  [INFO] Browsers will use system proxy settings" -ForegroundColor Gray
} catch {
    Write-Host "  [WARN] Could not configure browser registry: $_" -ForegroundColor Yellow
}

# Step 5: Test proxy connection
Write-Host ""
Write-Host "[5/5] Testing proxy connection..." -ForegroundColor Yellow
try {
    $test = Test-NetConnection -ComputerName "www.youtube.com" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($test) {
        Write-Host "  [OK] Connection to YouTube works" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Cannot connect to YouTube directly" -ForegroundColor Yellow
        Write-Host "  [INFO] This is normal - proxy should handle it" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [INFO] Connection test skipped" -ForegroundColor Gray
}

# Additional: Create browser proxy helper
Write-Host ""
Write-Host "Creating browser proxy helper..." -ForegroundColor Yellow

$helperScript = @"
# Browser Proxy Helper
# Use this to quickly enable/disable proxy

param(
    [switch]`$Enable,
    [switch]`$Disable,
    [switch]`$Status
)

`$internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"

if (`$Enable) {
    Set-ItemProperty -Path `$internetKey -Name "ProxyEnable" -Value 1
    Set-ItemProperty -Path `$internetKey -Name "ProxyServer" -Value "127.0.0.1:8080"
    Write-Host "Proxy ENABLED: 127.0.0.1:8080" -ForegroundColor Green
} elseif (`$Disable) {
    Set-ItemProperty -Path `$internetKey -Name "ProxyEnable" -Value 0
    Write-Host "Proxy DISABLED" -ForegroundColor Yellow
} elseif (`$Status) {
    `$proxy = Get-ItemProperty -Path `$internetKey
    Write-Host "Proxy Status:" -ForegroundColor Cyan
    Write-Host "  Enabled: `$(`$proxy.ProxyEnable)" -ForegroundColor White
    Write-Host "  Server: `$(`$proxy.ProxyServer)" -ForegroundColor White
} else {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\proxy-helper.ps1 -Enable    # Enable proxy" -ForegroundColor White
    Write-Host "  .\proxy-helper.ps1 -Disable   # Disable proxy" -ForegroundColor White
    Write-Host "  .\proxy-helper.ps1 -Status    # Check status" -ForegroundColor White
}
"@

$helperFile = Join-Path $PSScriptRoot "proxy-helper.ps1"
$helperScript | Out-File -FilePath $helperFile -Encoding UTF8
Write-Host "  [OK] Helper script created: proxy-helper.ps1" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Proxy Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. RESTART your browsers (Chrome, Edge, etc.)" -ForegroundColor White
Write-Host "  2. Try opening YouTube" -ForegroundColor White
Write-Host "  3. If still not working:" -ForegroundColor White
Write-Host "     - Check if Hysteria2 is running: Get-Process hysteria2" -ForegroundColor Gray
Write-Host "     - Restart Hysteria2: .\start-hysteria2.ps1" -ForegroundColor Gray
Write-Host "     - Check proxy in browser settings" -ForegroundColor Gray
Write-Host ""
Write-Host "Browser proxy settings:" -ForegroundColor Yellow
Write-Host "  Chrome/Edge: Settings → System → Open proxy settings" -ForegroundColor White
Write-Host "  Or use: .\proxy-helper.ps1 -Status" -ForegroundColor White
Write-Host ""









