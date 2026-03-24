# Complete Windows Optimization - All Steps
# Run as Administrator!

param(
    [switch]$All
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Optimization - All Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    $scriptDir = Get-Location
}
Set-Location $scriptDir

Write-Host "Script directory: $scriptDir" -ForegroundColor Gray
Write-Host ""

# Step 1: Clean
Write-Host "[1/4] Cleaning system..." -ForegroundColor Green
$cleanScript = Join-Path $scriptDir "clean-system.ps1"
if (Test-Path $cleanScript) {
    Write-Host "  Running: clean-system.ps1" -ForegroundColor Gray
    try {
        & $cleanScript 2>&1 | Out-Host
        Write-Host "  [DONE] Step 1 completed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Error in clean script: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] clean-system.ps1 not found!" -ForegroundColor Red
}
Write-Host ""
Write-Host "Continuing to next step..." -ForegroundColor Cyan
Write-Host ""

# Step 2: Performance
Write-Host "[2/4] Performance optimization..." -ForegroundColor Green
$perfScript = Join-Path $scriptDir "performance-tweaks.ps1"
if (Test-Path $perfScript) {
    Write-Host "  Running: performance-tweaks.ps1" -ForegroundColor Gray
    try {
        & $perfScript 2>&1 | Out-Host
        Write-Host "  [DONE] Step 2 completed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Error in performance script: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] performance-tweaks.ps1 not found!" -ForegroundColor Red
}
Write-Host ""
Write-Host "Continuing to next step..." -ForegroundColor Cyan
Write-Host ""

# Step 3: Security
Write-Host "[3/4] Security configuration..." -ForegroundColor Green
$secScript = Join-Path $scriptDir "security-tweaks.ps1"
if (Test-Path $secScript) {
    Write-Host "  Running: security-tweaks.ps1" -ForegroundColor Gray
    try {
        & $secScript 2>&1 | Out-Host
        Write-Host "  [DONE] Step 3 completed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Error in security script: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] security-tweaks.ps1 not found!" -ForegroundColor Red
}
Write-Host ""
Write-Host "Continuing to next step..." -ForegroundColor Cyan
Write-Host ""

# Step 4: Beauty
Write-Host "[4/4] Beautiful Windows theme..." -ForegroundColor Green
$beautyScript = Join-Path $scriptDir "beauty-tweaks.ps1"
if (Test-Path $beautyScript) {
    Write-Host "  Running: beauty-tweaks.ps1" -ForegroundColor Gray
    try {
        & $beautyScript 2>&1 | Out-Host
        Write-Host "  [DONE] Step 4 completed" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Error in beauty script: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] beauty-tweaks.ps1 not found!" -ForegroundColor Red
}
Write-Host ""

# Done
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Steps Completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Reboot recommended to apply all changes." -ForegroundColor Yellow
Write-Host ""

