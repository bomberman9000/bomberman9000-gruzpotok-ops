# Run All Optimization Steps - Force Execution
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Running ALL Optimization Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Set location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) { $scriptDir = Get-Location }
Set-Location $scriptDir

Write-Host "Working directory: $scriptDir" -ForegroundColor Gray
Write-Host ""

# Step 1: Clean (skip if already done)
Write-Host "[1/4] Step 1: Cleaning system..." -ForegroundColor Green
$cleanScript = "$scriptDir\clean-system.ps1"
if (Test-Path $cleanScript) {
    Write-Host "  Executing clean-system.ps1..." -ForegroundColor Gray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $cleanScript
    Write-Host "  [DONE] Step 1 completed" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] clean-system.ps1 not found" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Performance
Write-Host "[2/4] Step 2: Performance optimization..." -ForegroundColor Green
$perfScript = "$scriptDir\performance-tweaks.ps1"
if (Test-Path $perfScript) {
    Write-Host "  Executing performance-tweaks.ps1..." -ForegroundColor Gray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $perfScript
    Write-Host "  [DONE] Step 2 completed" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] performance-tweaks.ps1 not found" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Security
Write-Host "[3/4] Step 3: Security configuration..." -ForegroundColor Green
$secScript = "$scriptDir\security-tweaks.ps1"
if (Test-Path $secScript) {
    Write-Host "  Executing security-tweaks.ps1..." -ForegroundColor Gray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $secScript
    Write-Host "  [DONE] Step 3 completed" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] security-tweaks.ps1 not found" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Beauty
Write-Host "[4/4] Step 4: Beautiful Windows theme..." -ForegroundColor Green
$beautyScript = "$scriptDir\beauty-tweaks.ps1"
if (Test-Path $beautyScript) {
    Write-Host "  Executing beauty-tweaks.ps1..." -ForegroundColor Gray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $beautyScript
    Write-Host "  [DONE] Step 4 completed" -ForegroundColor Green
} else {
    Write-Host "  [SKIP] beauty-tweaks.ps1 not found" -ForegroundColor Yellow
}
Write-Host ""

# Done
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ALL STEPS COMPLETED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Reboot your computer to apply all changes." -ForegroundColor Yellow
Write-Host ""




