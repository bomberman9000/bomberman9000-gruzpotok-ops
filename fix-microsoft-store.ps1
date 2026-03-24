# Fix Microsoft Store - Remove restrictions
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Microsoft Store" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Enable Microsoft Store services
Write-Host "[1/5] Enabling Microsoft Store services..." -ForegroundColor Yellow

$services = @(
    "AppXSvc",              # Deployment Service
    "AppX Deployment Service",
    "WpnService",           # Windows Push Notifications
    "WpnUserService",       # Windows Push Notifications User Service
    "InstallService"        # Windows Installer
)

foreach ($serviceName in $services) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service) {
        try {
            if ($service.Status -ne "Running") {
                Start-Service -Name $serviceName -ErrorAction SilentlyContinue
            }
            Set-Service -Name $serviceName -StartupType Automatic -ErrorAction SilentlyContinue
            Write-Host "  [OK] Service enabled: $serviceName" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not enable: $serviceName" -ForegroundColor Yellow
        }
    }
}

# Fix registry restrictions
Write-Host ""
Write-Host "[2/5] Fixing registry restrictions..." -ForegroundColor Yellow

# Remove Store restrictions
$storeKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore"
)

foreach ($key in $storeKeys) {
    if (Test-Path $key) {
        try {
            Remove-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
            Write-Host "  [OK] Removed restrictions from: $key" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not remove restrictions from: $key" -ForegroundColor Yellow
        }
    }
}

# Enable Store in Group Policy locations
$gpoKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned\Microsoft.WindowsStore"
)

foreach ($key in $gpoKeys) {
    if (Test-Path $key) {
        try {
            Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  [OK] Removed restriction: $key" -ForegroundColor Green
        } catch {
            # Ignore errors
        }
    }
}

# Reset Windows Store cache
Write-Host ""
Write-Host "[3/5] Resetting Windows Store cache..." -ForegroundColor Yellow
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 3
    Write-Host "  [OK] Store cache reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset cache" -ForegroundColor Yellow
}

# Re-register Microsoft Store
Write-Host ""
Write-Host "[4/5] Re-registering Microsoft Store..." -ForegroundColor Yellow

$storeApp = Get-AppxPackage -Name "Microsoft.WindowsStore" -AllUsers -ErrorAction SilentlyContinue
if ($storeApp) {
    try {
        Add-AppxPackage -Register "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*\AppxManifest.xml" -DisableDevelopmentMode -ErrorAction SilentlyContinue
        Write-Host "  [OK] Store re-registered" -ForegroundColor Green
    } catch {
        # Try alternative method
        try {
            $manifestPath = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*\AppxManifest.xml" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($manifestPath) {
                Add-AppxPackage -Register $manifestPath.FullName -DisableDevelopmentMode -ErrorAction SilentlyContinue
                Write-Host "  [OK] Store re-registered (alternative method)" -ForegroundColor Green
            }
        } catch {
            Write-Host "  [WARN] Could not re-register Store" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [INFO] Store package not found, may need to reinstall" -ForegroundColor Yellow
}

# Enable Windows Update for Store apps
Write-Host ""
Write-Host "[5/5] Enabling Windows Update for Store apps..." -ForegroundColor Yellow

$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
if (-not (Test-Path $updateKey)) {
    New-Item -Path $updateKey -Force | Out-Null
}

Set-ItemProperty -Path $updateKey -Name "AutoDownload" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Windows Update enabled for Store apps" -ForegroundColor Green

# Reset network if needed
Write-Host ""
Write-Host "Resetting network components..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    Write-Host "  [OK] DNS cache flushed" -ForegroundColor Green
} catch {
    # Ignore
}

# Final steps
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Microsoft Store Fix Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer (recommended)" -ForegroundColor White
Write-Host "  2. Or restart Windows Explorer: taskkill /f /im explorer.exe && start explorer.exe" -ForegroundColor White
Write-Host "  3. Try opening Microsoft Store" -ForegroundColor White
Write-Host ""
Write-Host "If Store still doesn't work, try:" -ForegroundColor Yellow
Write-Host "  Get-AppXPackage *WindowsStore* | Reset-AppxPackage" -ForegroundColor White
Write-Host ""





