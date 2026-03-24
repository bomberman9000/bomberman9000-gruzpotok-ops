# Radical Microsoft Store Fix - All Methods
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Radical Microsoft Store Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Method 1: Complete Store Reset
Write-Host "[1/7] Complete Store Reset..." -ForegroundColor Yellow
try {
    Get-AppXPackage *WindowsStore* | Reset-AppxPackage -ErrorAction SilentlyContinue
    Write-Host "  [OK] Store completely reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset" -ForegroundColor Yellow
}

# Method 2: Remove and Reinstall Store
Write-Host ""
Write-Host "[2/7] Removing Store package..." -ForegroundColor Yellow
try {
    Get-AppxPackage Microsoft.WindowsStore | Remove-AppxPackage -ErrorAction SilentlyContinue
    Write-Host "  [OK] Store package removed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not remove package" -ForegroundColor Yellow
}

# Method 3: Reinstall Store from Provisioned Package
Write-Host ""
Write-Host "[3/7] Reinstalling Store..." -ForegroundColor Yellow
try {
    $provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"}
    if ($provisioned) {
        foreach ($pkg in $provisioned) {
            Add-AppxProvisionedPackage -Online -PackagePath $pkg.PackagePath -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Store reinstalled from provisioned package" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Provisioned package not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not reinstall" -ForegroundColor Yellow
}

# Method 4: Remove ALL Registry restrictions
Write-Host ""
Write-Host "[4/7] Removing ALL Registry restrictions..." -ForegroundColor Yellow

$regKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned",
    "HKCU:\Software\Policies\Microsoft\WindowsStore",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned"
)

foreach ($key in $regKeys) {
    if (Test-Path $key) {
        try {
            if ($key -like "*Deprovisioned*") {
                Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
            } else {
                Remove-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
                Remove-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
                Remove-ItemProperty -Path $key -Name "DisableStore" -ErrorAction SilentlyContinue
            }
            Write-Host "  [OK] Removed: $key" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not remove: $key" -ForegroundColor Yellow
        }
    }
}

# Method 5: Enable ALL required services
Write-Host ""
Write-Host "[5/7] Enabling ALL required services..." -ForegroundColor Yellow

$services = @(
    "AppXSvc",
    "WpnService", 
    "WpnUserService",
    "InstallService",
    "wuauserv",
    "BITS",
    "CryptSvc"
)

foreach ($svcName in $services) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if ($svc) {
        try {
            if ($svc.Status -ne "Running") {
                Start-Service -Name $svcName -ErrorAction SilentlyContinue
            }
            Set-Service -Name $svcName -StartupType Automatic -ErrorAction SilentlyContinue
            Write-Host "  [OK] Enabled: $svcName" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not enable: $svcName" -ForegroundColor Yellow
        }
    }
}

# Method 6: Reset Store cache and network
Write-Host ""
Write-Host "[6/7] Resetting cache and network..." -ForegroundColor Yellow
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 3
    ipconfig /flushdns | Out-Null
    netsh winsock reset | Out-Null
    Write-Host "  [OK] Cache and network reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset" -ForegroundColor Yellow
}

# Method 7: Re-register Store manually
Write-Host ""
Write-Host "[7/7] Re-registering Store manually..." -ForegroundColor Yellow
try {
    $storePaths = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*" -Directory -ErrorAction SilentlyContinue
    if ($storePaths) {
        foreach ($path in $storePaths) {
            $manifest = Join-Path $path.FullName "AppxManifest.xml"
            if (Test-Path $manifest) {
                Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction SilentlyContinue
                Write-Host "  [OK] Re-registered from: $($path.Name)" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "  [WARN] Store path not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not re-register" -ForegroundColor Yellow
}

# Final: Try to install Store for current user
Write-Host ""
Write-Host "Installing Store for current user..." -ForegroundColor Yellow
try {
    $provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"}
    if ($provisioned) {
        foreach ($pkg in $provisioned) {
            Add-AppxPackage -Register $pkg.PackagePath -DisableDevelopmentMode -ErrorAction SilentlyContinue
        }
        Write-Host "  [OK] Store installed for current user" -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Could not install for user" -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Radical Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL: Restart your computer NOW!" -ForegroundColor Red
Write-Host ""
Write-Host "After restart:" -ForegroundColor Yellow
Write-Host "  1. Try opening Microsoft Store" -ForegroundColor White
Write-Host "  2. If still not working, run Windows Update" -ForegroundColor White
Write-Host "  3. Check if Store service is running" -ForegroundColor White
Write-Host ""



