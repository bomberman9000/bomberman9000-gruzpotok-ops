# Check Microsoft Store Status
# Run as Administrator for full check

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Microsoft Store Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check 1: Store package for current user
Write-Host "[1/6] Checking Store package for current user..." -ForegroundColor Yellow
$store = Get-AppxPackage -Name "Microsoft.WindowsStore" -ErrorAction SilentlyContinue
if ($store) {
    Write-Host "  [OK] Store found!" -ForegroundColor Green
    Write-Host "    Package: $($store.PackageFullName)" -ForegroundColor Gray
    Write-Host "    Version: $($store.Version)" -ForegroundColor Gray
    Write-Host "    Install Location: $($store.InstallLocation)" -ForegroundColor Gray
} else {
    Write-Host "  [FAIL] Store NOT found for current user" -ForegroundColor Red
}

# Check 2: Provisioned package
Write-Host ""
Write-Host "[2/6] Checking provisioned Store package..." -ForegroundColor Yellow
$provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"} -ErrorAction SilentlyContinue
if ($provisioned) {
    Write-Host "  [OK] Provisioned package found!" -ForegroundColor Green
    Write-Host "    Display Name: $($provisioned.DisplayName)" -ForegroundColor Gray
    Write-Host "    Package Path: $($provisioned.PackagePath)" -ForegroundColor Gray
    if (Test-Path $provisioned.PackagePath) {
        Write-Host "    [OK] Package path exists" -ForegroundColor Green
    } else {
        Write-Host "    [FAIL] Package path does NOT exist" -ForegroundColor Red
    }
} else {
    Write-Host "  [FAIL] Provisioned package NOT found" -ForegroundColor Red
}

# Check 3: Store in WindowsApps
Write-Host ""
Write-Host "[3/6] Checking Store in WindowsApps folder..." -ForegroundColor Yellow
$storeDirs = Get-ChildItem "C:\Program Files\WindowsApps" -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -like "*WindowsStore*"}
if ($storeDirs) {
    Write-Host "  [OK] Store folders found!" -ForegroundColor Green
    foreach ($dir in $storeDirs) {
        Write-Host "    Folder: $($dir.Name)" -ForegroundColor Gray
        $manifest = Join-Path $dir.FullName "AppxManifest.xml"
        if (Test-Path $manifest) {
            Write-Host "      [OK] AppxManifest.xml exists" -ForegroundColor Green
        } else {
            Write-Host "      [FAIL] AppxManifest.xml NOT found" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  [FAIL] Store folders NOT found in WindowsApps" -ForegroundColor Red
}

# Check 4: Required services
Write-Host ""
Write-Host "[4/6] Checking required services..." -ForegroundColor Yellow
$services = @(
    @{Name="AppXSvc"; Display="AppX Deployment Service"},
    @{Name="WpnService"; Display="Windows Push Notifications"},
    @{Name="WpnUserService"; Display="Windows Push Notifications User"},
    @{Name="InstallService"; Display="Windows Installer"},
    @{Name="wuauserv"; Display="Windows Update"}
)

$allServicesOk = $true
foreach ($svc in $services) {
    $service = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq "Running") {
            Write-Host "  [OK] $($svc.Display) - Running" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] $($svc.Display) - $($service.Status)" -ForegroundColor Yellow
            $allServicesOk = $false
        }
        if ($service.StartType -eq "Automatic" -or $service.StartType -eq "AutomaticDelayedStart") {
            Write-Host "    [OK] Startup type: $($service.StartType)" -ForegroundColor Gray
        } else {
            Write-Host "    [WARN] Startup type: $($service.StartType)" -ForegroundColor Yellow
            $allServicesOk = $false
        }
    } else {
        Write-Host "  [FAIL] $($svc.Display) - NOT found" -ForegroundColor Red
        $allServicesOk = $false
    }
}

# Check 5: Registry restrictions
Write-Host ""
Write-Host "[5/6] Checking Registry restrictions..." -ForegroundColor Yellow
$regKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore"
)

$hasRestrictions = $false
foreach ($key in $regKeys) {
    if (Test-Path $key) {
        $removeStore = Get-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
        $disableApps = Get-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
        if ($removeStore -or $disableApps) {
            Write-Host "  [WARN] Restrictions found in: $key" -ForegroundColor Yellow
            if ($removeStore) { Write-Host "    RemoveWindowsStore: $($removeStore.RemoveWindowsStore)" -ForegroundColor Gray }
            if ($disableApps) { Write-Host "    DisableStoreApps: $($disableApps.DisableStoreApps)" -ForegroundColor Gray }
            $hasRestrictions = $true
        } else {
            Write-Host "  [OK] No restrictions in: $key" -ForegroundColor Green
        }
    } else {
        Write-Host "  [OK] Key does not exist: $key" -ForegroundColor Green
    }
}

# Check 6: Try to open Store
Write-Host ""
Write-Host "[6/6] Testing Store access..." -ForegroundColor Yellow
try {
    $storeApp = Get-StartApps | Where-Object {$_.Name -like "*Store*"}
    if ($storeApp) {
        Write-Host "  [OK] Store app found in Start menu" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Store app not found in Start menu" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not check Start menu: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($store) {
    Write-Host "[OK] Store is installed for current user" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Store is NOT installed for current user" -ForegroundColor Red
    Write-Host "  Action: Run restore-store.ps1" -ForegroundColor Yellow
}

if ($provisioned) {
    Write-Host "[OK] Provisioned package exists" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Provisioned package NOT found" -ForegroundColor Red
    Write-Host "  Action: Run restore-store.ps1" -ForegroundColor Yellow
}

if ($allServicesOk) {
    Write-Host "[OK] All required services are running" -ForegroundColor Green
} else {
    Write-Host "[WARN] Some services need attention" -ForegroundColor Yellow
    Write-Host "  Action: Run fix-store-simple.ps1" -ForegroundColor Yellow
}

if (-not $hasRestrictions) {
    Write-Host "[OK] No Registry restrictions found" -ForegroundColor Green
} else {
    Write-Host "[WARN] Registry restrictions found" -ForegroundColor Yellow
    Write-Host "  Action: Run fix-store-simple.ps1" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Recommended actions:" -ForegroundColor Cyan
if (-not $store) {
    Write-Host "  1. Run: .\restore-store.ps1" -ForegroundColor White
}
if (-not $allServicesOk) {
    Write-Host "  2. Run: .\fix-store-simple.ps1" -ForegroundColor White
}
if ($hasRestrictions) {
    Write-Host "  3. Run: .\fix-store-simple.ps1" -ForegroundColor White
}
if ($store -and $allServicesOk -and -not $hasRestrictions) {
    Write-Host "  Store should be working! Try opening it." -ForegroundColor Green
    Write-Host "  If not, restart your computer." -ForegroundColor Yellow
}
Write-Host ""


