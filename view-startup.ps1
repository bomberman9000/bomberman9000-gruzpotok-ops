# View Startup Programs
# No admin required

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Startup Programs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Startup folder
Write-Host "[1/3] Startup folder:" -ForegroundColor Yellow
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$commonStartupPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"

$found = $false
foreach ($path in @($startupPath, $commonStartupPath)) {
    if (Test-Path $path) {
        $items = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            Write-Host "  - $($item.Name)" -ForegroundColor White
            $found = $true
        }
    }
}

if (-not $found) {
    Write-Host "  (none)" -ForegroundColor Gray
}

# Registry startup
Write-Host ""
Write-Host "[2/3] Registry startup:" -ForegroundColor Yellow
$registryStartup = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    $found = $false
    foreach ($key in $regKeys) {
        Write-Host "  - $($key.Name): $($key.Value)" -ForegroundColor White
        $found = $true
    }
    if (-not $found) {
        Write-Host "  (none)" -ForegroundColor Gray
    }
} else {
    Write-Host "  (none)" -ForegroundColor Gray
}

# Task Scheduler startup
Write-Host ""
Write-Host "[3/3] Task Scheduler startup:" -ForegroundColor Yellow
try {
    $tasks = Get-ScheduledTask | Where-Object { 
        $_.State -eq "Ready" -and 
        $_.Settings.Enabled -eq $true -and
        ($_.Triggers | Where-Object { $_.Enabled -eq $true -and ($_.CimClass.CimClassName -eq "MSFT_TaskLogonTrigger" -or $_.CimClass.CimClassName -eq "MSFT_TaskBootTrigger") })
    }
    
    if ($tasks) {
        foreach ($task in $tasks) {
            Write-Host "  - $($task.TaskName)" -ForegroundColor White
        }
    } else {
        Write-Host "  (none)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Could not read Task Scheduler" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "To manage startup:" -ForegroundColor Yellow
Write-Host "  Task Manager → Startup tab" -ForegroundColor White
Write-Host "  Or: Settings → Apps → Startup" -ForegroundColor White
Write-Host ""









