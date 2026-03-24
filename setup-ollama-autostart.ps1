# Setup Ollama Autostart - Admin Required
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setting up Ollama Autostart" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Find Ollama
Write-Host "[1/3] Finding Ollama..." -ForegroundColor Yellow
$ollamaExe = "C:\Users\Shata\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        $ollamaExe = $ollamaCmd.Source
    } else {
        Write-Host "  [ERROR] Ollama not found!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  [OK] Ollama found: $ollamaExe" -ForegroundColor Green

# Check startup script
Write-Host ""
Write-Host "[2/3] Checking startup script..." -ForegroundColor Yellow
$startupScript = "$env:USERPROFILE\.ollama\start-ollama.ps1"
if (-not (Test-Path $startupScript)) {
    Write-Host "  [WARN] Startup script not found, creating..." -ForegroundColor Yellow
    
    $ollamaDir = Split-Path $ollamaExe -Parent
    if (-not (Test-Path (Split-Path $startupScript -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $startupScript -Parent) -Force | Out-Null
    }
    
    $scriptContent = @"
# Start Ollama on login
`$ollamaExe = "$ollamaExe"
`$ollamaDir = "$ollamaDir"

# Wait for system to be ready
Start-Sleep -Seconds 5

# Check if Ollama process is running
`$existing = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (`$existing) {
    exit 0
}

# Start Ollama
if (Test-Path `$ollamaExe) {
    Push-Location `$ollamaDir
    Start-Process -FilePath `$ollamaExe -WindowStyle Hidden
    Pop-Location
    Start-Sleep -Seconds 2
}
"@
    
    $scriptContent | Out-File -FilePath $startupScript -Encoding UTF8
    Write-Host "  [OK] Startup script created" -ForegroundColor Green
} else {
    Write-Host "  [OK] Startup script exists" -ForegroundColor Green
}

# Create Task Scheduler task
Write-Host ""
Write-Host "[3/3] Creating Task Scheduler task..." -ForegroundColor Yellow
$taskName = "Ollama-Startup"

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
    
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Start Ollama on login" -ErrorAction Stop | Out-Null
    
    Write-Host "  [OK] Task Scheduler task created" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Could not create task: $_" -ForegroundColor Red
    exit 1
}

# Verify and enable task
Write-Host ""
Write-Host "Verifying task..." -ForegroundColor Yellow
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "  [OK] Task verified" -ForegroundColor Green
    Enable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Write-Host "  [OK] Task enabled" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Task not found after creation!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Autostart Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ollama will start automatically on login!" -ForegroundColor Green
Write-Host ""
Write-Host "To test: Log out and log in again" -ForegroundColor Yellow
Write-Host ""








