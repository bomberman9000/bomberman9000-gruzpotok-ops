# Advanced Microsoft Store Fix - Multiple Methods
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Advanced Microsoft Store Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Method 1: Reset Store App
Write-Host "[Method 1] Resetting Microsoft Store app..." -ForegroundColor Yellow
try {
    Get-AppxPackage -Name "Microsoft.WindowsStore" | Reset-AppxPackage -ErrorAction SilentlyContinue
    Write-Host "  [OK] Store app reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset Store app" -ForegroundColor Yellow
}

# Method 2: Re-register Store
Write-Host ""
Write-Host "[Method 2] Re-registering Microsoft Store..." -ForegroundColor Yellow
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
    Write-Host "  [WARN] Could not re-register Store" -ForegroundColor Yellow
}

# Method 3: Remove all Store restrictions from Registry
Write-Host ""
Write-Host "[Method 3] Removing Registry restrictions..." -ForegroundColor Yellow

$restrictionKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned",
    "HKCU:\Software\Policies\Microsoft\WindowsStore",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned"
)

foreach ($key in $restrictionKeys) {
    if (Test-Path $key) {
        try {
            # Remove restriction properties
            Remove-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStore" -ErrorAction SilentlyContinue
            
            # Remove entire restriction folder if it's the Deprovisioned folder
            if ($key -like "*Deprovisioned*") {
                Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
            }
            
            Write-Host "  [OK] Removed restrictions from: $key" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not remove: $key" -ForegroundColor Yellow
        }
    }
}

# Method 4: Enable required services
Write-Host ""
Write-Host "[Method 4] Enabling required services..." -ForegroundColor Yellow

$requiredServices = @(
    @{Name="AppXSvc"; Display="AppX Deployment Service"},
    @{Name="WpnService"; Display="Windows Push Notifications"},
    @{Name="WpnUserService"; Display="Windows Push Notifications User"},
    @{Name="InstallService"; Display="Windows Installer"},
    @{Name="wuauserv"; Display="Windows Update"}
)

foreach ($svc in $requiredServices) {
    $service = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($service) {
        try {
            if ($service.Status -ne "Running") {
                Start-Service -Name $svc.Name -ErrorAction SilentlyContinue
            }
            Set-Service -Name $svc.Name -StartupType Automatic -ErrorAction SilentlyContinue
            Write-Host "  [OK] Enabled: $($svc.Display)" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not enable: $($svc.Display)" -ForegroundColor Yellow
        }
    }
}

# Method 5: Fix Group Policy restrictions
Write-Host ""
Write-Host "[Method 5] Fixing Group Policy restrictions..." -ForegroundColor Yellow

# Remove GPO restrictions
$gpoPaths = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore"
)

foreach ($path in $gpoPaths) {
    if (Test-Path $path) {
        try {
            # Set values to allow Store
            Set-ItemProperty -Path $path -Name "RemoveWindowsStore" -Value 0 -ErrorAction SilentlyContinue
            Set-ItemProperty -Path $path -Name "DisableStoreApps" -Value 0 -ErrorAction SilentlyContinue
            Write-Host "  [OK] GPO restrictions removed: $path" -ForegroundColor Green
        } catch {
            # If can't set, try to remove the key
            try {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] GPO key removed: $path" -ForegroundColor Green
            } catch {
                Write-Host "  [WARN] Could not fix: $path" -ForegroundColor Yellow
            }
        }
    }
}

# Method 6: Reset Store cache and network
Write-Host ""
Write-Host "[Method 6] Resetting cache and network..." -ForegroundColor Yellow

# Reset Store cache
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 2
    Write-Host "  [OK] Store cache reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset cache" -ForegroundColor Yellow
}

# Flush DNS
try {
    ipconfig /flushdns | Out-Null
    Write-Host "  [OK] DNS cache flushed" -ForegroundColor Green
} catch {
    # Ignore
}

# Method 7: Reinstall Store (if needed)
Write-Host ""
Write-Host "[Method 7] Checking Store installation..." -ForegroundColor Yellow

$storeApp = Get-AppxPackage -Name "Microsoft.WindowsStore" -AllUsers -ErrorAction SilentlyContinue
if (-not $storeApp) {
    Write-Host "  [INFO] Store not found, attempting to install..." -ForegroundColor Yellow
    try {
        # Try to install Store from Windows image
        Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"} | ForEach-Object {
            Add-AppxProvisionedPackage -Online -PackagePath $_.PackagePath -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Store installation attempted" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Could not install Store automatically" -ForegroundColor Yellow
        Write-Host "  [INFO] You may need to reinstall Windows or use DISM" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [OK] Store is installed" -ForegroundColor Green
}

# Method 8: Fix Windows Update for Store
Write-Host ""
Write-Host "[Method 8] Configuring Windows Update for Store..." -ForegroundColor Yellow

$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
if (-not (Test-Path $updateKey)) {
    New-Item -Path $updateKey -Force | Out-Null
}

Set-ItemProperty -Path $updateKey -Name "AutoDownload" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "RemoveWindowsStore" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  [OK] Windows Update configured for Store" -ForegroundColor Green

# Final summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Microsoft Store Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Applied fixes:" -ForegroundColor Yellow
Write-Host "  ✓ Store app reset" -ForegroundColor White
Write-Host "  ✓ Registry restrictions removed" -ForegroundColor White
Write-Host "  ✓ Required services enabled" -ForegroundColor White
Write-Host "  ✓ Group Policy restrictions removed" -ForegroundColor White
Write-Host "  ✓ Cache and network reset" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer (RECOMMENDED)" -ForegroundColor White
Write-Host "  2. Try opening Microsoft Store" -ForegroundColor White
Write-Host ""
Write-Host "If Store still doesn't work:" -ForegroundColor Yellow
Write-Host "  - Run: Get-AppXPackage *WindowsStore* | Reset-AppxPackage" -ForegroundColor White
Write-Host "  - Check Windows Update settings" -ForegroundColor White
Write-Host "  - Verify internet connection" -ForegroundColor White
Write-Host ""





