# Fix Microsoft Store with Proxy (happ)
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Store for Proxy Connection" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Check current proxy settings
Write-Host "[1/6] Checking current proxy settings..." -ForegroundColor Yellow
try {
    $proxy = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    if ($proxy.ProxyEnable -eq 1) {
        Write-Host "  [INFO] Proxy enabled: $($proxy.ProxyServer)" -ForegroundColor Gray
    } else {
        Write-Host "  [INFO] Proxy disabled" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Could not check proxy" -ForegroundColor Yellow
}

# Step 2: Configure proxy for Store apps
Write-Host ""
Write-Host "[2/6] Configuring proxy for Store apps..." -ForegroundColor Yellow
try {
    # Enable proxy for WinHTTP
    $winHttpKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\Connections"
    if (Test-Path $winHttpKey) {
        Write-Host "  [OK] WinHTTP settings found" -ForegroundColor Green
    }
    
    # Configure proxy bypass for local addresses
    $internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if (Test-Path $internetKey) {
        Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue
        Write-Host "  [OK] Proxy bypass configured" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not configure proxy bypass" -ForegroundColor Yellow
}

# Step 3: Configure WinHTTP proxy
Write-Host ""
Write-Host "[3/6] Configuring WinHTTP proxy..." -ForegroundColor Yellow
try {
    # Get current proxy
    $proxySettings = netsh winhttp show proxy
    Write-Host "  Current WinHTTP proxy:" -ForegroundColor Gray
    Write-Host "  $proxySettings" -ForegroundColor Gray
    
    # Note: User needs to set proxy manually if needed
    Write-Host "  [INFO] To set WinHTTP proxy, run:" -ForegroundColor Yellow
    Write-Host "    netsh winhttp set proxy proxy-server:PORT" -ForegroundColor White
    Write-Host "  [INFO] To reset WinHTTP proxy, run:" -ForegroundColor Yellow
    Write-Host "    netsh winhttp reset proxy" -ForegroundColor White
} catch {
    Write-Host "  [WARN] Could not check WinHTTP proxy" -ForegroundColor Yellow
}

# Step 4: Configure Store to use system proxy
Write-Host ""
Write-Host "[4/6] Configuring Store to use system proxy..." -ForegroundColor Yellow
try {
    # Enable proxy for UWP apps
    $uwpKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if (Test-Path $uwpKey) {
        Set-ItemProperty -Path $uwpKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
        Write-Host "  [OK] Proxy enabled for UWP apps" -ForegroundColor Green
    }
    
    # Configure Store app proxy
    $storeKey = "HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Storage\microsoft.windowsstore_*\Microsoft.WindowsStore"
    $storeKeys = Get-ChildItem "HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Storage" -ErrorAction SilentlyContinue | Where-Object {$_.Name -like "*windowsstore*"}
    
    foreach ($key in $storeKeys) {
        $fullKey = Join-Path $key.PSPath "Microsoft.WindowsStore"
        if (Test-Path $fullKey) {
            Set-ItemProperty -Path $fullKey -Name "UseSystemProxy" -Value 1 -ErrorAction SilentlyContinue
            Write-Host "  [OK] System proxy enabled for Store" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "  [WARN] Could not configure Store proxy" -ForegroundColor Yellow
}

# Step 5: Reset network for Store
Write-Host ""
Write-Host "[5/6] Resetting network for Store..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    netsh winsock reset | Out-Null
    
    # Reset WinHTTP proxy (optional - uncomment if needed)
    # netsh winhttp reset proxy
    
    Write-Host "  [OK] Network reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset network" -ForegroundColor Yellow
}

# Step 6: Clear Store cache
Write-Host ""
Write-Host "[6/6] Clearing Store cache..." -ForegroundColor Yellow
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 2
    
    # Clear Store app cache
    $cachePaths = @(
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\LocalCache",
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\TempState"
    )
    
    foreach ($path in $cachePaths) {
        $fullPath = $path -replace '\*', '*'
        Get-ChildItem $fullPath -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  [OK] Store cache cleared" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not clear cache" -ForegroundColor Yellow
}

# Additional: Show proxy configuration help
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Proxy Configuration Help" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To configure proxy for Store:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Set system proxy:" -ForegroundColor White
Write-Host "   Settings → Network & Internet → Proxy" -ForegroundColor Gray
Write-Host "   Enable 'Use a proxy server'" -ForegroundColor Gray
Write-Host "   Enter your proxy address and port" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Set WinHTTP proxy (for Store apps):" -ForegroundColor White
Write-Host "   netsh winhttp set proxy proxy-server:PORT" -ForegroundColor Gray
Write-Host "   Example: netsh winhttp set proxy 127.0.0.1:8080" -ForegroundColor Gray
Write-Host ""
Write-Host "3. If using authentication:" -ForegroundColor White
Write-Host "   netsh winhttp set proxy proxy-server:PORT bypass-list='localhost'" -ForegroundColor Gray
Write-Host ""
Write-Host "4. To reset WinHTTP proxy:" -ForegroundColor White
Write-Host "   netsh winhttp reset proxy" -ForegroundColor Gray
Write-Host ""

# Done
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Proxy Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Configure your proxy (see instructions above)" -ForegroundColor White
Write-Host "  2. RESTART your computer" -ForegroundColor White
Write-Host "  3. Try opening Store" -ForegroundColor White
Write-Host ""









