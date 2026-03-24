# Verify Store Fix Applied
# Run as Administrator for full check

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verifying Store Fix Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allOk = $true
$issues = @()

# Check 1: Store package
Write-Host "[1/7] Checking Store package..." -ForegroundColor Yellow
$store = Get-AppxPackage -Name "Microsoft.WindowsStore" -ErrorAction SilentlyContinue
if ($store) {
    Write-Host "  [OK] Store installed: $($store.Version)" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Store NOT installed" -ForegroundColor Red
    $allOk = $false
    $issues += "Store package not found"
}

# Check 2: Required services
Write-Host ""
Write-Host "[2/7] Checking required services..." -ForegroundColor Yellow
$services = @(
    @{Name="AppXSvc"; Display="AppX Deployment Service"},
    @{Name="WpnService"; Display="Windows Push Notifications"},
    @{Name="WpnUserService"; Display="Windows Push Notifications User"},
    @{Name="InstallService"; Display="Windows Installer"},
    @{Name="wuauserv"; Display="Windows Update"},
    @{Name="BITS"; Display="Background Intelligent Transfer"},
    @{Name="CryptSvc"; Display="Cryptographic Services"}
)

$servicesOk = $true
foreach ($svc in $services) {
    $service = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq "Running") {
            Write-Host "  [OK] $($svc.Display) - Running" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $($svc.Display) - $($service.Status)" -ForegroundColor Red
            $servicesOk = $false
            $allOk = $false
            $issues += "$($svc.Display) is not running"
        }
    } else {
        Write-Host "  [WARN] $($svc.Display) - NOT found" -ForegroundColor Yellow
    }
}

# Check 3: Registry restrictions
Write-Host ""
Write-Host "[3/7] Checking Registry restrictions..." -ForegroundColor Yellow
$regKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsStore"
)

$restrictionsOk = $true
foreach ($key in $regKeys) {
    if (Test-Path $key) {
        $removeStore = Get-ItemProperty -Path $key -Name "RemoveWindowsStore" -ErrorAction SilentlyContinue
        $disableApps = Get-ItemProperty -Path $key -Name "DisableStoreApps" -ErrorAction SilentlyContinue
        if ($removeStore -and $removeStore.RemoveWindowsStore -ne 0) {
            Write-Host "  [FAIL] Restriction found: RemoveWindowsStore = $($removeStore.RemoveWindowsStore)" -ForegroundColor Red
            $restrictionsOk = $false
            $allOk = $false
            $issues += "Registry restriction: RemoveWindowsStore"
        }
        if ($disableApps -and $disableApps.DisableStoreApps -ne 0) {
            Write-Host "  [FAIL] Restriction found: DisableStoreApps = $($disableApps.DisableStoreApps)" -ForegroundColor Red
            $restrictionsOk = $false
            $allOk = $false
            $issues += "Registry restriction: DisableStoreApps"
        }
        if ($restrictionsOk) {
            Write-Host "  [OK] No restrictions in: $key" -ForegroundColor Green
        }
    } else {
        Write-Host "  [OK] Key does not exist: $key" -ForegroundColor Green
    }
}

# Check 4: Windows Update configuration
Write-Host ""
Write-Host "[4/7] Checking Windows Update configuration..." -ForegroundColor Yellow
$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore"
if (Test-Path $updateKey) {
    $autoDownload = Get-ItemProperty -Path $updateKey -Name "AutoDownload" -ErrorAction SilentlyContinue
    $allowUpdate = Get-ItemProperty -Path $updateKey -Name "AllowAutoUpdate" -ErrorAction SilentlyContinue
    if ($autoDownload -and $autoDownload.AutoDownload -eq 2) {
        Write-Host "  [OK] AutoDownload configured correctly" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] AutoDownload not configured" -ForegroundColor Yellow
    }
    if ($allowUpdate -and $allowUpdate.AllowAutoUpdate -eq 1) {
        Write-Host "  [OK] AllowAutoUpdate enabled" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] AllowAutoUpdate not enabled" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WARN] Update key not found" -ForegroundColor Yellow
}

# Check 5: Network connectivity
Write-Host ""
Write-Host "[5/7] Checking network connectivity..." -ForegroundColor Yellow
try {
    $test = Test-NetConnection -ComputerName www.microsoft.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($test) {
        Write-Host "  [OK] Internet connection working" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Internet connection not working" -ForegroundColor Red
        $allOk = $false
        $issues += "Internet connection not working"
    }
} catch {
    Write-Host "  [WARN] Could not test connection" -ForegroundColor Yellow
}

# Check 6: Store cache
Write-Host ""
Write-Host "[6/7] Checking Store cache..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\LocalCache",
    "$env:LOCALAPPDATA\Packages\Microsoft.WindowsStore_*\TempState"
)

$cacheExists = $false
foreach ($path in $cachePaths) {
    $fullPath = $path -replace '\*', '*'
    $cache = Get-ChildItem $fullPath -ErrorAction SilentlyContinue
    if ($cache) {
        $cacheExists = $true
        Write-Host "  [INFO] Cache found (this is normal)" -ForegroundColor Gray
        break
    }
}
if (-not $cacheExists) {
    Write-Host "  [OK] Cache cleared (as expected)" -ForegroundColor Green
}

# Check 7: Store accessibility
Write-Host ""
Write-Host "[7/7] Checking Store accessibility..." -ForegroundColor Yellow
try {
    $storeApp = Get-StartApps | Where-Object {$_.Name -like "*Store*"}
    if ($storeApp) {
        Write-Host "  [OK] Store found in Start menu" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Store not found in Start menu" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not check Start menu" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($store) {
    Write-Host "[OK] Store package: INSTALLED" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Store package: NOT INSTALLED" -ForegroundColor Red
}

if ($servicesOk) {
    Write-Host "[OK] Services: ALL RUNNING" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Services: SOME NOT RUNNING" -ForegroundColor Red
}

if ($restrictionsOk) {
    Write-Host "[OK] Registry: NO RESTRICTIONS" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Registry: RESTRICTIONS FOUND" -ForegroundColor Red
}

Write-Host ""
if ($allOk) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Store should be working correctly!" -ForegroundColor Green
    Write-Host ""
    Write-Host "If Store still doesn't work:" -ForegroundColor Yellow
    Write-Host "  1. Make sure you RESTARTED the computer" -ForegroundColor White
    Write-Host "  2. Try opening Store and wait 1-2 minutes" -ForegroundColor White
    Write-Host "  3. Check your Microsoft account login" -ForegroundColor White
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ISSUES FOUND" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Found issues:" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "Recommended action:" -ForegroundColor Yellow
    Write-Host "  Run: .\fix-store-working.ps1" -ForegroundColor White
    Write-Host "  Then restart your computer" -ForegroundColor White
}
Write-Host ""

