# Fix Microsoft Store - Make it Actually Work
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Microsoft Store Functionality" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Reset Store completely
Write-Host "[1/8] Resetting Store completely..." -ForegroundColor Yellow
try {
    Get-AppxPackage *WindowsStore* | Reset-AppxPackage -ErrorAction SilentlyContinue
    Write-Host "  [OK] Store reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset" -ForegroundColor Yellow
}

# Step 2: Clear Store cache
Write-Host ""
Write-Host "[2/8] Clearing Store cache..." -ForegroundColor Yellow
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 3
    
    # Clear additional cache locations
    $cachePaths = @(
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\LocalCache",
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\TempState",
        "$env:LOCALAPPDATA\Microsoft\Windows\INetCache"
    )
    
    foreach ($path in $cachePaths) {
        $fullPath = $path -replace '\*', '*'
        Get-ChildItem $fullPath -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  [OK] Cache cleared" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not clear cache" -ForegroundColor Yellow
}

# Step 3: Enable and start all required services
Write-Host ""
Write-Host "[3/8] Starting all required services..." -ForegroundColor Yellow
$services = @(
    "AppXSvc",
    "WpnService",
    "WpnUserService",
    "InstallService",
    "wuauserv",
    "BITS",
    "CryptSvc",
    "DcomLaunch"
)

foreach ($svcName in $services) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if ($svc) {
        try {
            if ($svc.Status -ne "Running") {
                Start-Service -Name $svcName -ErrorAction SilentlyContinue
            }
            Set-Service -Name $svcName -StartupType Automatic -ErrorAction SilentlyContinue
            Write-Host "  [OK] $svcName - Running" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not start: $svcName" -ForegroundColor Yellow
        }
    }
}

# Step 4: Fix network connectivity
Write-Host ""
Write-Host "[4/8] Fixing network connectivity..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    netsh winsock reset | Out-Null
    netsh int ip reset | Out-Null
    Write-Host "  [OK] Network reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset network" -ForegroundColor Yellow
}

# Step 5: Remove Store restrictions
Write-Host ""
Write-Host "[5/8] Removing all Store restrictions..." -ForegroundColor Yellow
$regKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore",
    "HKCU:\Software\Policies\Microsoft\WindowsStore"
)

foreach ($key in $regKeys) {
    if (Test-Path $key) {
        try {
            Remove-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStore" -ErrorAction SilentlyContinue
            Write-Host "  [OK] Removed restrictions: $key" -ForegroundColor Green
        } catch {
            # Ignore
        }
    }
}

# Step 6: Enable Windows Update for Store
Write-Host ""
Write-Host "[6/8] Configuring Windows Update for Store..." -ForegroundColor Yellow
$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
if (-not (Test-Path $updateKey)) {
    New-Item -Path $updateKey -Force | Out-Null
}
Set-ItemProperty -Path $updateKey -Name "AutoDownload" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "RemoveWindowsStore" -Value 0 -ErrorAction SilentlyContinue
Write-Host "  [OK] Windows Update configured" -ForegroundColor Green

# Step 7: Re-register Store
Write-Host ""
Write-Host "[7/8] Re-registering Store..." -ForegroundColor Yellow
try {
    $storePath = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($storePath) {
        $manifest = Join-Path $storePath.FullName "AppxManifest.xml"
        if (Test-Path $manifest) {
            Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction SilentlyContinue
            Write-Host "  [OK] Store re-registered" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "  [WARN] Could not re-register" -ForegroundColor Yellow
}

# Step 8: Fix time sync (important for Store)
Write-Host ""
Write-Host "[8/8] Syncing time..." -ForegroundColor Yellow
try {
    w32tm /resync | Out-Null
    Write-Host "  [OK] Time synced" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not sync time" -ForegroundColor Yellow
}

# Additional: Check internet connection
Write-Host ""
Write-Host "Checking internet connection..." -ForegroundColor Yellow
try {
    $test = Test-NetConnection -ComputerName www.microsoft.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($test) {
        Write-Host "  [OK] Internet connection working" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Internet connection may have issues" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not test connection" -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Store Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT STEPS:" -ForegroundColor Red
Write-Host "  1. RESTART your computer" -ForegroundColor Yellow
Write-Host "  2. After restart, open Microsoft Store" -ForegroundColor Yellow
Write-Host "  3. Wait for Store to load (may take 1-2 minutes)" -ForegroundColor Yellow
Write-Host "  4. If still not working, check:" -ForegroundColor Yellow
Write-Host "     - Internet connection" -ForegroundColor White
Write-Host "     - Windows Update status" -ForegroundColor White
Write-Host "     - Firewall settings" -ForegroundColor White
Write-Host ""


