# Check if an application is installed and available
# Usage: .\check-application.ps1 -ApplicationName "appname" -ExecutablePath "app.exe"

param(
    [Parameter(Mandatory=$true)]
    [string]$ApplicationName,
    
    [Parameter(Mandatory=$false)]
    [string[]]$ExecutablePaths,
    
    [Parameter(Mandatory=$false)]
    [string]$AlternativeMethod
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Checking: $ApplicationName" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$found = $false
$foundPath = $null

# Check if specific paths were provided
if ($ExecutablePaths) {
    Write-Host "Checking provided paths..." -ForegroundColor Yellow
    foreach ($path in $ExecutablePaths) {
        if (Test-Path $path) {
            $found = $true
            $foundPath = $path
            Write-Host "  [OK] Found at: $path" -ForegroundColor Green
            break
        } else {
            Write-Host "  [INFO] Not found: $path" -ForegroundColor Gray
        }
    }
}

# Check if running as process
if (-not $found) {
    Write-Host ""
    Write-Host "Checking running processes..." -ForegroundColor Yellow
    $process = Get-Process -Name $ApplicationName -ErrorAction SilentlyContinue
    if ($process) {
        $found = $true
        $foundPath = $process.Path
        Write-Host "  [OK] Application is running: $($process.Path)" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Application is not running" -ForegroundColor Gray
    }
}

# Check via Get-Command
if (-not $found) {
    Write-Host ""
    Write-Host "Checking system PATH..." -ForegroundColor Yellow
    $command = Get-Command $ApplicationName -ErrorAction SilentlyContinue
    if ($command) {
        $found = $true
        $foundPath = $command.Source
        Write-Host "  [OK] Found in PATH: $($command.Source)" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Not found in PATH" -ForegroundColor Gray
    }
}

# Check AppX packages for UWP apps
if (-not $found) {
    Write-Host ""
    Write-Host "Checking Windows Store apps..." -ForegroundColor Yellow
    $appx = Get-AppxPackage | Where-Object { $_.Name -like "*$ApplicationName*" } | Select-Object -First 1
    if ($appx) {
        $found = $true
        Write-Host "  [OK] Found Store app: $($appx.Name)" -ForegroundColor Green
        Write-Host "      Package: $($appx.PackageFullName)" -ForegroundColor Gray
        $foundPath = "AppX:$($appx.PackageFamilyName)"
    } else {
        Write-Host "  [INFO] Not found in Store apps" -ForegroundColor Gray
    }
}

# Results
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($found) {
    Write-Host "  RESULT: Application found!" -ForegroundColor Green
    Write-Host "  Path: $foundPath" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  RESULT: Application not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "The application '$ApplicationName' does not appear to be installed." -ForegroundColor Yellow
    Write-Host ""
    if ($AlternativeMethod) {
        Write-Host "Alternative method:" -ForegroundColor Cyan
        Write-Host "  $AlternativeMethod" -ForegroundColor White
    } else {
        Write-Host "Suggestions:" -ForegroundColor Cyan
        Write-Host "  1. Check if the application is installed" -ForegroundColor White
        Write-Host "  2. Verify the installation path" -ForegroundColor White
        Write-Host "  3. Try reinstalling the application" -ForegroundColor White
    }
    exit 1
}
