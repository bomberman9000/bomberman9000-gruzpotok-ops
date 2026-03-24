# Reinstall Microsoft Store - Correct Method
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Reinstalling Microsoft Store" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Remove Store for current user
Write-Host "[1/4] Removing Store for current user..." -ForegroundColor Yellow
try {
    $store = Get-AppxPackage -Name "Microsoft.WindowsStore" -ErrorAction SilentlyContinue
    if ($store) {
        Remove-AppxPackage -Package $store.PackageFullName -ErrorAction SilentlyContinue
        Write-Host "  [OK] Store removed for current user" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Store not found for current user" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Could not remove: $_" -ForegroundColor Yellow
}

# Step 2: Get provisioned package
Write-Host ""
Write-Host "[2/4] Finding provisioned Store package..." -ForegroundColor Yellow
try {
    $provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"}
    if ($provisioned) {
        Write-Host "  [OK] Found provisioned package: $($provisioned.DisplayName)" -ForegroundColor Green
        $packagePath = $provisioned.PackagePath
        Write-Host "  Package path: $packagePath" -ForegroundColor Gray
    } else {
        Write-Host "  [ERROR] Provisioned package not found!" -ForegroundColor Red
        Write-Host "  Store may need to be restored from Windows image" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  [ERROR] Could not find provisioned package: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Reinstall for all users
Write-Host ""
Write-Host "[3/4] Reinstalling Store for all users..." -ForegroundColor Yellow
try {
    if (Test-Path $packagePath) {
        Add-AppxProvisionedPackage -Online -PackagePath $packagePath -ErrorAction Stop
        Write-Host "  [OK] Store reinstalled for all users" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Package path not found: $packagePath" -ForegroundColor Red
    }
} catch {
    Write-Host "  [WARN] Could not reinstall for all users: $_" -ForegroundColor Yellow
    Write-Host "  Trying alternative method..." -ForegroundColor Gray
    
    # Alternative: Try to find Store in WindowsApps
    $storePath = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($storePath) {
        $manifest = Join-Path $storePath.FullName "AppxManifest.xml"
        if (Test-Path $manifest) {
            try {
                Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction SilentlyContinue
                Write-Host "  [OK] Store registered from WindowsApps" -ForegroundColor Green
            } catch {
                Write-Host "  [ERROR] Could not register: $_" -ForegroundColor Red
            }
        }
    }
}

# Step 4: Install for current user
Write-Host ""
Write-Host "[4/4] Installing Store for current user..." -ForegroundColor Yellow
try {
    if (Test-Path $packagePath) {
        # Find manifest in package
        $manifestPath = Join-Path $packagePath "AppxManifest.xml"
        if (Test-Path $manifestPath) {
            Add-AppxPackage -Register $manifestPath -DisableDevelopmentMode -ErrorAction Stop
            Write-Host "  [OK] Store installed for current user" -ForegroundColor Green
        } else {
            # Try to find in WindowsApps
            $storePath = Get-ChildItem "C:\Program Files\WindowsApps\Microsoft.WindowsStore_*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($storePath) {
                $manifest = Join-Path $storePath.FullName "AppxManifest.xml"
                if (Test-Path $manifest) {
                    Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction Stop
                    Write-Host "  [OK] Store installed from WindowsApps" -ForegroundColor Green
                }
            }
        }
    }
} catch {
    Write-Host "  [WARN] Could not install for current user: $_" -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Reinstallation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer" -ForegroundColor White
Write-Host "  2. Try opening Microsoft Store" -ForegroundColor White
Write-Host ""
Write-Host "If Store still doesn't work, you may need to:" -ForegroundColor Yellow
Write-Host "  - Run Windows Update" -ForegroundColor White
Write-Host "  - Restore Store from Windows image using DISM" -ForegroundColor White
Write-Host ""



