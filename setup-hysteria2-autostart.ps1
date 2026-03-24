# Setup Hysteria2 Autostart
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting up Hysteria2 Autostart" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Check Hysteria2
Write-Host "[1/4] Checking Hysteria2..." -ForegroundColor Yellow
$hysteria2Exe = "C:\Program Files\hysteria2\hysteria2.exe"
if (-not (Test-Path $hysteria2Exe)) {
    $hysteria2Cmd = Get-Command hysteria2 -ErrorAction SilentlyContinue
    if ($hysteria2Cmd) {
        $hysteria2Exe = $hysteria2Cmd.Source
    } else {
        Write-Host "  [ERROR] Hysteria2 not found!" -ForegroundColor Red
        Write-Host "  [INFO] Run setup-hysteria2.ps1 first" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  [OK] Hysteria2 found: $hysteria2Exe" -ForegroundColor Green

# Check config
Write-Host ""
Write-Host "[2/4] Checking config..." -ForegroundColor Yellow
$configFile = "$env:USERPROFILE\.hysteria2\config.yaml"
if (-not (Test-Path $configFile)) {
    Write-Host "  [ERROR] Config file not found: $configFile" -ForegroundColor Red
    Write-Host "  [INFO] Run setup-hysteria2.ps1 first" -ForegroundColor Yellow
    exit 1
}
Write-Host "  [OK] Config found: $configFile" -ForegroundColor Green

# Create startup script
Write-Host ""
Write-Host "[3/4] Creating startup script..." -ForegroundColor Yellow
$startupScript = "$env:USERPROFILE\.hysteria2\start-hysteria2.ps1"

$scriptContent = @"
# Start Hysteria2 on login
`$hysteria2Exe = "$hysteria2Exe"
`$configFile = "$configFile"

# Wait a bit for system to be ready
Start-Sleep -Seconds 5

# Check if already running
`$existing = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (`$existing) {
    exit 0
}

# Start Hysteria2
if (Test-Path `$hysteria2Exe) {
    Start-Process -FilePath `$hysteria2Exe -ArgumentList "-c", `$configFile -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
"@

$scriptContent | Out-File -FilePath $startupScript -Encoding UTF8
Write-Host "  [OK] Startup script created: $startupScript" -ForegroundColor Green

# Create Task Scheduler task
Write-Host ""
Write-Host "[4/4] Creating Task Scheduler task..." -ForegroundColor Yellow
$taskName = "Hysteria2-Startup"

# Remove existing task if any
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "  [INFO] Removed existing task" -ForegroundColor Gray
}

# Create new task
try {
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startupScript`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Start Hysteria2 VPN on login" -ErrorAction Stop | Out-Null
    
    Write-Host "  [OK] Task Scheduler task created" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Could not create task: $_" -ForegroundColor Red
    exit 1
}

# Verify task
Write-Host ""
Write-Host "Verifying task..." -ForegroundColor Yellow
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "  [OK] Task verified" -ForegroundColor Green
    Write-Host "  State: $($task.State)" -ForegroundColor Gray
    Write-Host "  Enabled: $($task.Settings.Enabled)" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Task not found after creation" -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Autostart Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Hysteria2 will start automatically on login!" -ForegroundColor Green
Write-Host ""
Write-Host "To test:" -ForegroundColor Yellow
Write-Host "  1. Log out and log in again" -ForegroundColor White
Write-Host "  2. Or restart your computer" -ForegroundColor White
Write-Host "  3. Check if Hysteria2 is running: Get-Process hysteria2" -ForegroundColor White
Write-Host ""
Write-Host "To disable autostart:" -ForegroundColor Yellow
Write-Host "  Disable-ScheduledTask -TaskName `"$taskName`"" -ForegroundColor White
Write-Host ""









