# Windows Optimization Script
# Run as Administrator!

param(
    [switch]$Clean,
    [switch]$Performance,
    [switch]$Security,
    [switch]$Beauty,
    [switch]$All
)

# Check admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the file and select 'Run as administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Optimization" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script root
if ($PSScriptRoot) {
    $scriptRoot = $PSScriptRoot
} else {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (-not $scriptRoot) {
        $scriptRoot = Get-Location
    }
}

if ($All -or $Clean) {
    Write-Host "[1/4] Cleaning system..." -ForegroundColor Green
    $cleanScript = Join-Path $scriptRoot "clean-system.ps1"
    if (Test-Path $cleanScript) {
        & $cleanScript
    } else {
        Write-Host "  ERROR: clean-system.ps1 not found!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Performance) {
    Write-Host "[2/4] Performance optimization..." -ForegroundColor Green
    $perfScript = Join-Path $scriptRoot "performance-tweaks.ps1"
    if (Test-Path $perfScript) {
        & $perfScript
    } else {
        Write-Host "  ERROR: performance-tweaks.ps1 not found!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Security) {
    Write-Host "[3/4] Security configuration..." -ForegroundColor Green
    $secScript = Join-Path $scriptRoot "security-tweaks.ps1"
    if (Test-Path $secScript) {
        & $secScript
    } else {
        Write-Host "  ERROR: security-tweaks.ps1 not found!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Beauty) {
    Write-Host "[4/4] Beautiful Windows theme..." -ForegroundColor Green
    $beautyScript = Join-Path $scriptRoot "beauty-tweaks.ps1"
    if (Test-Path $beautyScript) {
        & $beautyScript
    } else {
        Write-Host "  ERROR: beauty-tweaks.ps1 not found!" -ForegroundColor Red
    }
    Write-Host ""
}

if (-not ($Clean -or $Performance -or $Security -or $Beauty -or $All)) {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\optimize-windows-fixed.ps1 -All              # All optimizations + beauty" -ForegroundColor White
    Write-Host "  .\optimize-windows-fixed.ps1 -Clean            # Clean only" -ForegroundColor White
    Write-Host "  .\optimize-windows-fixed.ps1 -Performance      # Performance only" -ForegroundColor White
    Write-Host "  .\optimize-windows-fixed.ps1 -Security         # Security only" -ForegroundColor White
    Write-Host "  .\optimize-windows-fixed.ps1 -Beauty           # Beauty only" -ForegroundColor White
    exit 0
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Optimization completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Reboot recommended." -ForegroundColor Yellow





