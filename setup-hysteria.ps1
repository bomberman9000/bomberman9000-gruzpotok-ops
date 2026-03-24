# Setup Hysteria VPN/Proxy
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Check if Hysteria is installed
Write-Host "[1/6] Checking Hysteria installation..." -ForegroundColor Yellow
$hysteriaExe = $null
$possiblePaths = @(
    "C:\Program Files\hysteria\hysteria.exe",
    "C:\Program Files (x86)\hysteria\hysteria.exe",
    "$env:USERPROFILE\hysteria\hysteria.exe",
    "$env:LOCALAPPDATA\hysteria\hysteria.exe",
    ".\hysteria.exe",
    "hysteria.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $hysteriaExe = $path
        Write-Host "  [OK] Found Hysteria: $path" -ForegroundColor Green
        break
    }
}

# Check in PATH
if (-not $hysteriaExe) {
    $hysteriaCmd = Get-Command hysteria -ErrorAction SilentlyContinue
    if ($hysteriaCmd) {
        $hysteriaExe = $hysteriaCmd.Source
        Write-Host "  [OK] Found Hysteria in PATH: $hysteriaExe" -ForegroundColor Green
    }
}

if (-not $hysteriaExe) {
    Write-Host "  [WARN] Hysteria not found" -ForegroundColor Yellow
    Write-Host "  [INFO] You need to download Hysteria first" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Download from: https://github.com/apernet/hysteria/releases" -ForegroundColor Cyan
    Write-Host "  Or run: .\download-hysteria.ps1" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}

# Step 2: Create config directory
Write-Host ""
Write-Host "[2/6] Creating config directory..." -ForegroundColor Yellow
$configDir = "$env:USERPROFILE\.hysteria"
if (-not (Test-Path $configDir)) {
    New-Item -Path $configDir -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created: $configDir" -ForegroundColor Green
} else {
    Write-Host "  [OK] Directory exists: $configDir" -ForegroundColor Green
}

# Step 3: Create config file template
Write-Host ""
Write-Host "[3/6] Creating config file..." -ForegroundColor Yellow
$configFile = Join-Path $configDir "config.json"

if (-not (Test-Path $configFile)) {
    $configTemplate = @{
        server = "your-server:port"
        auth = "your-auth-string"
        bandwidth = @{
            up = "20 Mbps"
            down = "100 Mbps"
        }
        socks5 = @{
            listen = "127.0.0.1:1080"
        }
        http = @{
            listen = "127.0.0.1:8080"
        }
    }
    
    $configJson = $configTemplate | ConvertTo-Json -Depth 10
    $configJson | Out-File -FilePath $configFile -Encoding UTF8
    Write-Host "  [OK] Config template created: $configFile" -ForegroundColor Green
    Write-Host "  [INFO] Please edit config.json with your server details" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] Config file exists: $configFile" -ForegroundColor Green
}

# Step 4: Create startup script
Write-Host ""
Write-Host "[4/6] Creating startup script..." -ForegroundColor Yellow
$startupScript = Join-Path $configDir "start-hysteria.ps1"

$scriptContent = @"
# Start Hysteria
`$hysteriaExe = "$hysteriaExe"
`$configFile = "$configFile"

if (Test-Path `$hysteriaExe) {
    Write-Host "Starting Hysteria..." -ForegroundColor Green
    Start-Process -FilePath `$hysteriaExe -ArgumentList "-c", `$configFile -WindowStyle Hidden
    Write-Host "Hysteria started!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Hysteria not found at `$hysteriaExe" -ForegroundColor Red
}
"@

$scriptContent | Out-File -FilePath $startupScript -Encoding UTF8
Write-Host "  [OK] Startup script created: $startupScript" -ForegroundColor Green

# Step 5: Configure proxy settings
Write-Host ""
Write-Host "[5/6] Configuring proxy settings..." -ForegroundColor Yellow
try {
    # Set WinHTTP proxy (for Store and UWP apps)
    Write-Host "  [INFO] Configuring WinHTTP proxy..." -ForegroundColor Gray
    Write-Host "  [INFO] Default: 127.0.0.1:8080 (HTTP) or 127.0.0.1:1080 (SOCKS5)" -ForegroundColor Gray
    
    # Ask user for proxy type
    Write-Host ""
    $proxyType = Read-Host "Proxy type? (1=HTTP:8080, 2=SOCKS5:1080, 3=Skip)"
    
    if ($proxyType -eq "1") {
        netsh winhttp set proxy 127.0.0.1:8080
        Write-Host "  [OK] WinHTTP proxy set to HTTP: 127.0.0.1:8080" -ForegroundColor Green
    } elseif ($proxyType -eq "2") {
        netsh winhttp set proxy proxy-server=127.0.0.1:1080
        Write-Host "  [OK] WinHTTP proxy set to SOCKS5: 127.0.0.1:1080" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] Proxy configuration skipped" -ForegroundColor Yellow
    }
    
    # Configure system proxy
    $internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    if ($proxyType -eq "1" -or $proxyType -eq "2") {
        Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
        if ($proxyType -eq "1") {
            Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] System proxy configured" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not configure proxy: $_" -ForegroundColor Yellow
}

# Step 6: Create service (optional)
Write-Host ""
Write-Host "[6/6] Creating Windows service (optional)..." -ForegroundColor Yellow
Write-Host "  [INFO] To run Hysteria as service, use NSSM:" -ForegroundColor Gray
Write-Host "    1. Download NSSM from https://nssm.cc/download" -ForegroundColor Gray
Write-Host "    2. Run: nssm install Hysteria `"$hysteriaExe`" `"-c $configFile`"" -ForegroundColor Gray
Write-Host "    3. Or use Task Scheduler for startup" -ForegroundColor Gray

# Create Task Scheduler task
Write-Host ""
Write-Host "Creating Task Scheduler task..." -ForegroundColor Yellow
try {
    $taskName = "Hysteria-Startup"
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    }
    
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startupScript`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Start Hysteria on login" -ErrorAction SilentlyContinue | Out-Null
    
    Write-Host "  [OK] Task Scheduler task created" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not create task: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Config file: $configFile" -ForegroundColor White
Write-Host "  Startup script: $startupScript" -ForegroundColor White
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Edit config.json with your server details:" -ForegroundColor White
Write-Host "     - server: your-server-address:port" -ForegroundColor Gray
Write-Host "     - auth: your-auth-string" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start Hysteria:" -ForegroundColor White
Write-Host "     .\start-hysteria.ps1" -ForegroundColor Gray
Write-Host "     Or: $startupScript" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Hysteria will start automatically on login" -ForegroundColor White
Write-Host ""
Write-Host "  4. Test connection:" -ForegroundColor White
Write-Host "     Open browser and check if proxy works" -ForegroundColor Gray
Write-Host ""









