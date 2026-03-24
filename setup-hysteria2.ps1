# Setup Hysteria2 with provided server
# Run as Administrator!

param(
    [string]$ServerUrl = "hysteria2://Samara128500@144.31.64.130:4443/?sni=144.31.64.130&insecure=1#Hysteria2-Server"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria2 Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Parse server URL
Write-Host "[1/6] Parsing server configuration..." -ForegroundColor Yellow
$serverUrl = $ServerUrl

# Extract components from hysteria2:// URL
if ($serverUrl -match "hysteria2://([^@]+)@([^/]+)/([^#]+)#(.+)") {
    $auth = $matches[1]
    $server = $matches[2]
    $params = $matches[3]
    $name = $matches[4]
    
    Write-Host "  [OK] Server: $server" -ForegroundColor Green
    Write-Host "  [OK] Auth: $auth" -ForegroundColor Green
    Write-Host "  [OK] Name: $name" -ForegroundColor Green
    
    # Parse parameters
    $sni = $null
    $insecure = $false
    if ($params -match "sni=([^&]+)") {
        $sni = $matches[1]
        Write-Host "  [OK] SNI: $sni" -ForegroundColor Green
    }
    if ($params -match "insecure=1") {
        $insecure = $true
        Write-Host "  [OK] Insecure: true" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] Invalid server URL format" -ForegroundColor Red
    exit 1
}

# Step 2: Check/Download Hysteria2
Write-Host ""
Write-Host "[2/6] Checking Hysteria2 installation..." -ForegroundColor Yellow
$hysteria2Exe = $null
$possiblePaths = @(
    "C:\Program Files\hysteria2\hysteria2.exe",
    "C:\Program Files (x86)\hysteria2\hysteria2.exe",
    "$env:USERPROFILE\hysteria2\hysteria2.exe",
    "$env:LOCALAPPDATA\hysteria2\hysteria2.exe",
    ".\hysteria2.exe",
    "hysteria2.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $hysteria2Exe = $path
        Write-Host "  [OK] Found Hysteria2: $path" -ForegroundColor Green
        break
    }
}

# Check in PATH
if (-not $hysteria2Exe) {
    $hysteria2Cmd = Get-Command hysteria2 -ErrorAction SilentlyContinue
    if ($hysteria2Cmd) {
        $hysteria2Exe = $hysteria2Cmd.Source
        Write-Host "  [OK] Found Hysteria2 in PATH: $hysteria2Exe" -ForegroundColor Green
    }
}

if (-not $hysteria2Exe) {
    Write-Host "  [WARN] Hysteria2 not found" -ForegroundColor Yellow
    Write-Host "  [INFO] Downloading Hysteria2..." -ForegroundColor Yellow
    
    # Download Hysteria2
    $arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
    $downloadDir = "$env:USERPROFILE\Downloads\hysteria2"
    if (-not (Test-Path $downloadDir)) {
        New-Item -Path $downloadDir -ItemType Directory -Force | Out-Null
    }
    
    $latestUrl = "https://github.com/apernet/hysteria/releases/latest/download/hysteria-windows-$arch.exe"
    $outputFile = Join-Path $downloadDir "hysteria2.exe"
    
    try {
        Write-Host "  Downloading from GitHub..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $latestUrl -OutFile $outputFile -UseBasicParsing -ErrorAction Stop
        Write-Host "  [OK] Downloaded: $outputFile" -ForegroundColor Green
        
        # Install to Program Files
        $installDir = "C:\Program Files\hysteria2"
        if (-not (Test-Path $installDir)) {
            New-Item -Path $installDir -ItemType Directory -Force | Out-Null
        }
        $installFile = Join-Path $installDir "hysteria2.exe"
        Copy-Item -Path $outputFile -Destination $installFile -Force
        $hysteria2Exe = $installFile
        Write-Host "  [OK] Installed to: $installFile" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Could not download: $_" -ForegroundColor Red
        Write-Host "  [INFO] Please download manually from:" -ForegroundColor Yellow
        Write-Host "    https://github.com/apernet/hysteria/releases" -ForegroundColor Cyan
        exit 1
    }
}

# Step 3: Create config directory
Write-Host ""
Write-Host "[3/6] Creating config directory..." -ForegroundColor Yellow
$configDir = "$env:USERPROFILE\.hysteria2"
if (-not (Test-Path $configDir)) {
    New-Item -Path $configDir -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created: $configDir" -ForegroundColor Green
} else {
    Write-Host "  [OK] Directory exists: $configDir" -ForegroundColor Green
}

# Step 4: Create config file
Write-Host ""
Write-Host "[4/6] Creating config file..." -ForegroundColor Yellow
$configFile = Join-Path $configDir "config.yaml"

# Hysteria2 config format
$configContent = @"
server: $server
auth: $auth
bandwidth:
  up: 20 Mbps
  down: 100 Mbps
socks5:
  listen: 127.0.0.1:1080
http:
  listen: 127.0.0.1:8080
tls:
  sni: $sni
  insecure: $insecure
"@

$configContent | Out-File -FilePath $configFile -Encoding UTF8
Write-Host "  [OK] Config created: $configFile" -ForegroundColor Green

# Step 5: Configure proxy
Write-Host ""
Write-Host "[5/6] Configuring proxy settings..." -ForegroundColor Yellow
try {
    # Set WinHTTP proxy for Store
    netsh winhttp set proxy 127.0.0.1:8080
    Write-Host "  [OK] WinHTTP proxy set to: 127.0.0.1:8080" -ForegroundColor Green
    
    # Set system proxy
    $internetKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    Set-ItemProperty -Path $internetKey -Name "ProxyEnable" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyServer" -Value "127.0.0.1:8080" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $internetKey -Name "ProxyOverride" -Value "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;172.28.*;172.29.*;172.30.*;172.31.*;192.168.*;<local>" -ErrorAction SilentlyContinue
    Write-Host "  [OK] System proxy configured" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not configure proxy: $_" -ForegroundColor Yellow
}

# Step 6: Create startup script and service
Write-Host ""
Write-Host "[6/6] Creating startup script..." -ForegroundColor Yellow
$startupScript = Join-Path $configDir "start-hysteria2.ps1"

$scriptContent = @"
# Start Hysteria2
`$hysteria2Exe = "$hysteria2Exe"
`$configFile = "$configFile"

if (Test-Path `$hysteria2Exe) {
    Write-Host "Starting Hysteria2..." -ForegroundColor Green
    Start-Process -FilePath `$hysteria2Exe -ArgumentList "-c", `$configFile -WindowStyle Hidden
    Start-Sleep -Seconds 2
    `$process = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
    if (`$process) {
        Write-Host "Hysteria2 started! PID: `$(`$process.Id)" -ForegroundColor Green
    } else {
        Write-Host "Hysteria2 may have failed to start. Check logs." -ForegroundColor Yellow
    }
} else {
    Write-Host "ERROR: Hysteria2 not found at `$hysteria2Exe" -ForegroundColor Red
}
"@

$scriptContent | Out-File -FilePath $startupScript -Encoding UTF8
Write-Host "  [OK] Startup script created: $startupScript" -ForegroundColor Green

# Create Task Scheduler task
Write-Host ""
Write-Host "Creating Task Scheduler task..." -ForegroundColor Yellow
try {
    $taskName = "Hysteria2-Startup"
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    }
    
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startupScript`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Start Hysteria2 on login" -ErrorAction SilentlyContinue | Out-Null
    
    Write-Host "  [OK] Task Scheduler task created" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not create task: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Hysteria2 Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Server: $server" -ForegroundColor White
Write-Host "  Config file: $configFile" -ForegroundColor White
Write-Host "  Startup script: $startupScript" -ForegroundColor White
Write-Host "  Proxy: 127.0.0.1:8080 (HTTP), 127.0.0.1:1080 (SOCKS5)" -ForegroundColor White
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Start Hysteria2:" -ForegroundColor White
Write-Host "     .\start-hysteria2.ps1" -ForegroundColor Gray
Write-Host "     Or: $startupScript" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Hysteria2 will start automatically on login" -ForegroundColor White
Write-Host ""
Write-Host "  3. Test connection:" -ForegroundColor White
Write-Host "     Open browser and check if proxy works" -ForegroundColor Gray
Write-Host "     Open Microsoft Store - should work now!" -ForegroundColor Gray
Write-Host ""









