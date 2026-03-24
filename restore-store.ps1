# Restore Microsoft Store from Windows Image
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Restoring Microsoft Store" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Check current Store status
Write-Host "[1/5] Checking Store status..." -ForegroundColor Yellow
$store = Get-AppxPackage -Name "Microsoft.WindowsStore" -ErrorAction SilentlyContinue
if ($store) {
    Write-Host "  [INFO] Store found: $($store.PackageFullName)" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Store not found for current user" -ForegroundColor Yellow
}

$provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"} -ErrorAction SilentlyContinue
if ($provisioned) {
    Write-Host "  [INFO] Provisioned package found: $($provisioned.DisplayName)" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Provisioned package not found" -ForegroundColor Yellow
}

# Step 2: Restore Windows image health
Write-Host ""
Write-Host "[2/5] Restoring Windows image health..." -ForegroundColor Yellow
Write-Host "  This may take 10-20 minutes..." -ForegroundColor Gray
try {
    $result = dism /online /cleanup-image /restorehealth
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Windows image restored" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] DISM returned code: $LASTEXITCODE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not run DISM: $_" -ForegroundColor Yellow
}

# Step 3: Run System File Checker
Write-Host ""
Write-Host "[3/5] Running System File Checker..." -ForegroundColor Yellow
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Gray
try {
    sfc /scannow
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] System files checked" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] SFC returned code: $LASTEXITCODE" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARN] Could not run SFC: $_" -ForegroundColor Yellow
}

# Step 4: Try to reinstall Store from Windows image
Write-Host ""
Write-Host "[4/5] Reinstalling Store from Windows image..." -ForegroundColor Yellow
try {
    # Method 1: Use DISM to restore Store
    Write-Host "  Trying DISM method..." -ForegroundColor Gray
    $dismResult = dism /online /get-provisionedappxpackages | Select-String "WindowsStore"
    if ($dismResult) {
        Write-Host "  [OK] Store found in Windows image" -ForegroundColor Green
    }
    
    # Method 2: Try to find and register Store from WindowsApps
    Write-Host "  Searching for Store in WindowsApps..." -ForegroundColor Gray
    $storeDirs = Get-ChildItem "C:\Program Files\WindowsApps" -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -like "*WindowsStore*"}
    
    if ($storeDirs) {
        foreach ($dir in $storeDirs) {
            $manifest = Join-Path $dir.FullName "AppxManifest.xml"
            if (Test-Path $manifest) {
                Write-Host "  [OK] Found Store in: $($dir.Name)" -ForegroundColor Green
                try {
                    Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction Stop
                    Write-Host "  [OK] Store registered successfully" -ForegroundColor Green
                    break
                } catch {
                    Write-Host "  [WARN] Could not register: $_" -ForegroundColor Yellow
                }
            }
        }
    } else {
        Write-Host "  [WARN] Store not found in WindowsApps" -ForegroundColor Yellow
    }
    
    # Method 3: Try provisioned package
    Write-Host "  Trying provisioned package..." -ForegroundColor Gray
    $provisioned = Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -like "*WindowsStore*"} -ErrorAction SilentlyContinue
    if ($provisioned) {
        try {
            # Get the actual package path
            $packagePath = $provisioned.PackagePath
            if ($packagePath -and (Test-Path $packagePath)) {
                $manifest = Join-Path $packagePath "AppxManifest.xml"
                if (Test-Path $manifest) {
                    Add-AppxPackage -Register $manifest -DisableDevelopmentMode -ErrorAction Stop
                    Write-Host "  [OK] Store installed from provisioned package" -ForegroundColor Green
                }
            }
        } catch {
            Write-Host "  [WARN] Could not install from provisioned package: $_" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "  [ERROR] Could not reinstall Store: $_" -ForegroundColor Red
}

# Step 5: Final check
Write-Host ""
Write-Host "[5/5] Final check..." -ForegroundColor Yellow
$finalCheck = Get-AppxPackage -Name "Microsoft.WindowsStore" -ErrorAction SilentlyContinue
if ($finalCheck) {
    Write-Host "  [OK] Store is now installed!" -ForegroundColor Green
    Write-Host "  Package: $($finalCheck.PackageFullName)" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Store still not found" -ForegroundColor Yellow
    Write-Host "  You may need to:" -ForegroundColor Yellow
    Write-Host "    1. Run Windows Update" -ForegroundColor White
    Write-Host "    2. Reinstall Windows Store from Microsoft website" -ForegroundColor White
    Write-Host "    3. Use Windows Reset (Settings > Recovery)" -ForegroundColor White
}

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Restoration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL: Restart your computer NOW!" -ForegroundColor Red
Write-Host ""
Write-Host "After restart, try opening Microsoft Store." -ForegroundColor Yellow
Write-Host ""


