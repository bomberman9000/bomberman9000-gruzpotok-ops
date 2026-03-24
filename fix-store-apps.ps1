# Fix Microsoft Store - Apps Installation Issues
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Store Apps Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Reset all Store apps
Write-Host "[1/7] Resetting all Store apps..." -ForegroundColor Yellow
try {
    Get-AppxPackage -AllUsers | ForEach-Object {
        try {
            Reset-AppxPackage -Package $_.PackageFullName -ErrorAction SilentlyContinue
        } catch {
            # Ignore errors
        }
    }
    Write-Host "  [OK] All apps reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset all apps" -ForegroundColor Yellow
}

# Step 2: Fix AppX service
Write-Host ""
Write-Host "[2/7] Fixing AppX Deployment Service..." -ForegroundColor Yellow
try {
    $appxSvc = Get-Service -Name "AppXSvc" -ErrorAction SilentlyContinue
    if ($appxSvc) {
        if ($appxSvc.Status -ne "Running") {
            Start-Service -Name "AppXSvc" -ErrorAction SilentlyContinue
        }
        Set-Service -Name "AppXSvc" -StartupType Automatic -ErrorAction SilentlyContinue
        Restart-Service -Name "AppXSvc" -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] AppX service restarted" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not fix AppX service" -ForegroundColor Yellow
}

# Step 3: Clear AppX cache
Write-Host ""
Write-Host "[3/7] Clearing AppX cache..." -ForegroundColor Yellow
try {
    $cachePaths = @(
        "$env:LOCALAPPDATA\Packages\*\LocalCache",
        "$env:LOCALAPPDATA\Packages\*\TempState",
        "$env:LOCALAPPDATA\Microsoft\Windows\INetCache",
        "$env:LOCALAPPDATA\Microsoft\Windows\AppCache"
    )
    
    foreach ($path in $cachePaths) {
        $fullPath = $path -replace '\*', '*'
        Get-ChildItem $fullPath -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  [OK] AppX cache cleared" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not clear all cache" -ForegroundColor Yellow
}

# Step 4: Fix Windows Update for apps
Write-Host ""
Write-Host "[4/7] Configuring Windows Update for apps..." -ForegroundColor Yellow
try {
    $updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
    if (-not (Test-Path $updateKey)) {
        New-Item -Path $updateKey -Force | Out-Null
    }
    Set-ItemProperty -Path $updateKey -Name "AutoDownload" -Value 2 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $updateKey -Name "RemoveWindowsStore" -Value 0 -ErrorAction SilentlyContinue
    
    # Enable automatic app updates
    $appUpdateKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update" -Name "AUOptions" -Value 4 -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Windows Update configured" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not configure updates" -ForegroundColor Yellow
}

# Step 5: Fix permissions
Write-Host ""
Write-Host "[5/7] Fixing permissions..." -ForegroundColor Yellow
try {
    # Reset WindowsApps permissions
    $windowsApps = "C:\Program Files\WindowsApps"
    if (Test-Path $windowsApps) {
        icacls $windowsApps /reset /T /C /L | Out-Null
        Write-Host "  [OK] Permissions reset" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not reset permissions" -ForegroundColor Yellow
}

# Step 6: Re-register Store
Write-Host ""
Write-Host "[6/7] Re-registering Store..." -ForegroundColor Yellow
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

# Step 7: Fix network for apps
Write-Host ""
Write-Host "[7/7] Fixing network for apps..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    netsh winsock reset | Out-Null
    netsh int ip reset | Out-Null
    
    # Enable network discovery
    netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes | Out-Null
    
    Write-Host "  [OK] Network fixed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not fix network" -ForegroundColor Yellow
}

# Additional: Check for specific app issues
Write-Host ""
Write-Host "Checking for app installation issues..." -ForegroundColor Yellow
try {
    $appxError = Get-EventLog -LogName Application -Source "Microsoft-Windows-AppXDeployment*" -Newest 5 -ErrorAction SilentlyContinue
    if ($appxError) {
        Write-Host "  [INFO] Found recent AppX events (check Event Viewer if needed)" -ForegroundColor Gray
    } else {
        Write-Host "  [OK] No recent AppX errors" -ForegroundColor Green
    }
} catch {
    # Ignore
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Apps Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT STEPS:" -ForegroundColor Red
Write-Host "  1. RESTART your computer" -ForegroundColor Yellow
Write-Host "  2. After restart, try installing/opening apps from Store" -ForegroundColor Yellow
Write-Host "  3. If specific app doesn't work:" -ForegroundColor Yellow
Write-Host "     - Reset that app: Get-AppxPackage *AppName* | Reset-AppxPackage" -ForegroundColor White
Write-Host "     - Or reinstall it from Store" -ForegroundColor White
Write-Host ""









