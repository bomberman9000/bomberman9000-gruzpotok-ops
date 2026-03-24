# Microsoft Store Fix - Simple Version
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Microsoft Store" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Reset Store
Write-Host "[1/6] Resetting Store app..." -ForegroundColor Yellow
try {
    Get-AppxPackage -Name "Microsoft.WindowsStore" | Reset-AppxPackage -ErrorAction SilentlyContinue
    Write-Host "  [OK] Store reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset" -ForegroundColor Yellow
}

# Step 2: Remove Registry restrictions
Write-Host ""
Write-Host "[2/6] Removing Registry restrictions..." -ForegroundColor Yellow

$keys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Appx\AppxAllUserStore\Deprovisioned"
)

foreach ($key in $keys) {
    if (Test-Path $key) {
        try {
            Remove-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path $key -Name "DisableStore" -ErrorAction SilentlyContinue
            
            if ($key -like "*Deprovisioned*") {
                Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
            }
            Write-Host "  [OK] Removed: $key" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Could not remove: $key" -ForegroundColor Yellow
        }
    }
}

# Step 3: Enable services
Write-Host ""
Write-Host "[3/6] Enabling services..." -ForegroundColor Yellow

$services = @("AppXSvc", "WpnService", "WpnUserService", "InstallService", "wuauserv")
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

# Step 4: Re-register Store
Write-Host ""
Write-Host "[4/6] Re-registering Store..." -ForegroundColor Yellow
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

# Step 5: Reset cache
Write-Host ""
Write-Host "[5/6] Resetting cache..." -ForegroundColor Yellow
try {
    wsreset.exe | Out-Null
    Start-Sleep -Seconds 2
    ipconfig /flushdns | Out-Null
    Write-Host "  [OK] Cache reset" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not reset cache" -ForegroundColor Yellow
}

# Step 6: Configure Windows Update
Write-Host ""
Write-Host "[6/6] Configuring Windows Update..." -ForegroundColor Yellow
$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
if (-not (Test-Path $updateKey)) {
    New-Item -Path $updateKey -Force | Out-Null
}
Set-ItemProperty -Path $updateKey -Name "AutoDownload" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $updateKey -Name "RemoveWindowsStore" -Value 0 -ErrorAction SilentlyContinue
Write-Host "  [OK] Windows Update configured" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Microsoft Store Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer" -ForegroundColor White
Write-Host "  2. Try opening Microsoft Store" -ForegroundColor White
Write-Host ""
Write-Host "If still not working, run:" -ForegroundColor Yellow
Write-Host "  Get-AppXPackage *WindowsStore* | Reset-AppxPackage" -ForegroundColor White
Write-Host ""





