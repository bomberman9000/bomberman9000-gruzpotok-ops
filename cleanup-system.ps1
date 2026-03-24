# Cleanup System - Remove Unnecessary Programs, Shortcuts, Configure Startup
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  System Cleanup and Startup Config" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Remove unnecessary UWP apps
Write-Host "[1/5] Removing unnecessary UWP apps..." -ForegroundColor Yellow
$appsToRemove = @(
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.Xbox.TCUI",
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.BingNews",
    "Microsoft.BingWeather",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "Microsoft.MicrosoftOfficeHub",
    "Microsoft.MicrosoftStickyNotes",
    "Microsoft.People",
    "Microsoft.SkypeApp",
    "Microsoft.YourPhone",
    "Microsoft.ZuneMusic",
    "Microsoft.ZuneVideo",
    "Microsoft.3DBuilder",
    "Microsoft.WindowsMaps",
    "Microsoft.WindowsAlarms",
    "Microsoft.WindowsCamera",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.WindowsSoundRecorder",
    "Microsoft.MixedReality.Portal"
)

$removed = 0
foreach ($app in $appsToRemove) {
    $package = Get-AppxPackage -Name $app -ErrorAction SilentlyContinue
    if ($package) {
        try {
            Write-Host "  Removing: $app" -ForegroundColor Gray
            Remove-AppxPackage -Package $package.PackageFullName -ErrorAction SilentlyContinue
            $removed++
        } catch {
            Write-Host "  [WARN] Could not remove: $app" -ForegroundColor Yellow
        }
    }
}

if ($removed -gt 0) {
    Write-Host "  [OK] Removed $removed apps" -ForegroundColor Green
} else {
    Write-Host "  [OK] No unnecessary apps found" -ForegroundColor Green
}

# Step 2: Clean desktop shortcuts
Write-Host ""
Write-Host "[2/5] Cleaning desktop shortcuts..." -ForegroundColor Yellow
$desktop = [Environment]::GetFolderPath("Desktop")
$publicDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")

$shortcutsToRemove = @(
    "*Microsoft Edge*",
    "*Office*",
    "*Skype*",
    "*Xbox*",
    "*Get Started*",
    "*Mail*",
    "*Calendar*"
)

$removedShortcuts = 0
foreach ($path in @($desktop, $publicDesktop)) {
    if (Test-Path $path) {
        foreach ($pattern in $shortcutsToRemove) {
            $files = Get-ChildItem -Path $path -Filter $pattern -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                try {
                    Write-Host "  Removing: $($file.Name)" -ForegroundColor Gray
                    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
                    $removedShortcuts++
                } catch {
                    Write-Host "  [WARN] Could not remove: $($file.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedShortcuts -gt 0) {
    Write-Host "  [OK] Removed $removedShortcuts shortcuts" -ForegroundColor Green
} else {
    Write-Host "  [OK] No unnecessary shortcuts found" -ForegroundColor Green
}

# Step 3: Clean Start Menu shortcuts
Write-Host ""
Write-Host "[3/5] Cleaning Start Menu shortcuts..." -ForegroundColor Yellow
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$commonStartMenu = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"

$removedStartMenu = 0
foreach ($path in @($startMenu, $commonStartMenu)) {
    if (Test-Path $path) {
        foreach ($pattern in $shortcutsToRemove) {
            $files = Get-ChildItem -Path $path -Filter $pattern -Recurse -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                try {
                    Write-Host "  Removing: $($file.Name)" -ForegroundColor Gray
                    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
                    $removedStartMenu++
                } catch {
                    Write-Host "  [WARN] Could not remove: $($file.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedStartMenu -gt 0) {
    Write-Host "  [OK] Removed $removedStartMenu Start Menu shortcuts" -ForegroundColor Green
} else {
    Write-Host "  [OK] No unnecessary Start Menu shortcuts found" -ForegroundColor Green
}

# Step 4: Configure startup (remove unnecessary, keep important)
Write-Host ""
Write-Host "[4/5] Configuring startup programs..." -ForegroundColor Yellow

# Get startup programs
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$commonStartupPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"

# Programs to keep in startup
$keepInStartup = @(
    "Hysteria2",
    "hysteria2"
)

# Remove unnecessary startup items
$removedStartup = 0
foreach ($path in @($startupPath, $commonStartupPath)) {
    if (Test-Path $path) {
        $items = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            $shouldKeep = $false
            foreach ($keep in $keepInStartup) {
                if ($item.Name -like "*$keep*") {
                    $shouldKeep = $true
                    break
                }
            }
            
            if (-not $shouldKeep) {
                # Check if it's a known unnecessary program
                $unnecessary = @("Skype", "Xbox", "Office", "OneDrive", "Teams", "Discord", "Steam")
                $isUnnecessary = $false
                foreach ($unwanted in $unnecessary) {
                    if ($item.Name -like "*$unwanted*") {
                        $isUnnecessary = $true
                        break
                    }
                }
                
                if ($isUnnecessary) {
                    try {
                        Write-Host "  Removing from startup: $($item.Name)" -ForegroundColor Gray
                        Remove-Item -Path $item.FullName -Force -ErrorAction SilentlyContinue
                        $removedStartup++
                    } catch {
                        Write-Host "  [WARN] Could not remove: $($item.Name)" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
}

# Also check registry startup
$registryStartup = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    foreach ($key in $regKeys) {
        $shouldKeep = $false
        foreach ($keep in $keepInStartup) {
            if ($key.Name -like "*$keep*" -or $key.Value -like "*$keep*") {
                $shouldKeep = $true
                break
            }
        }
        
        if (-not $shouldKeep) {
            $unnecessary = @("Skype", "Xbox", "Teams", "Discord", "Steam", "Spotify")
            $isUnnecessary = $false
            foreach ($unwanted in $unnecessary) {
                if ($key.Name -like "*$unwanted*" -or $key.Value -like "*$unwanted*") {
                    $isUnnecessary = $true
                    break
                }
            }
            
            if ($isUnnecessary) {
                try {
                    Write-Host "  Removing from registry startup: $($key.Name)" -ForegroundColor Gray
                    Remove-ItemProperty -Path $registryStartup -Name $key.Name -ErrorAction SilentlyContinue
                    $removedStartup++
                } catch {
                    Write-Host "  [WARN] Could not remove: $($key.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedStartup -gt 0) {
    Write-Host "  [OK] Removed $removedStartup startup items" -ForegroundColor Green
} else {
    Write-Host "  [OK] No unnecessary startup items found" -ForegroundColor Green
}

# Step 5: Show current startup
Write-Host ""
Write-Host "[5/5] Current startup programs:" -ForegroundColor Yellow
Write-Host ""

# Startup folder
Write-Host "Startup folder:" -ForegroundColor Cyan
foreach ($path in @($startupPath, $commonStartupPath)) {
    if (Test-Path $path) {
        $items = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            Write-Host "  - $($item.Name)" -ForegroundColor White
        }
    }
}

# Registry startup
Write-Host ""
Write-Host "Registry startup:" -ForegroundColor Cyan
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    foreach ($key in $regKeys) {
        Write-Host "  - $($key.Name)" -ForegroundColor White
    }
} else {
    Write-Host "  (none)" -ForegroundColor Gray
}

# Task Scheduler startup
Write-Host ""
Write-Host "Task Scheduler startup:" -ForegroundColor Cyan
$tasks = Get-ScheduledTask | Where-Object { $_.Settings.RunOnlyIfLoggedOn -eq $false -and $_.State -eq "Ready" -and $_.Triggers.Enabled -eq $true } | Where-Object { $_.Triggers.TriggerType -eq "Logon" }
foreach ($task in $tasks) {
    Write-Host "  - $($task.TaskName)" -ForegroundColor White
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  - Removed unnecessary UWP apps" -ForegroundColor White
Write-Host "  - Cleaned desktop shortcuts" -ForegroundColor White
Write-Host "  - Cleaned Start Menu shortcuts" -ForegroundColor White
Write-Host "  - Configured startup programs" -ForegroundColor White
Write-Host ""
Write-Host "To manage startup manually:" -ForegroundColor Yellow
Write-Host "  Task Manager → Startup tab" -ForegroundColor White
Write-Host "  Or: Settings → Apps → Startup" -ForegroundColor White
Write-Host ""









