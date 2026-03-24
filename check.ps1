# Quick check script
$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) { $scriptRoot = Get-Location }

Write-Host "Checking scripts..." -ForegroundColor Cyan

$files = @("optimize-windows.ps1", "clean-system.ps1", "performance-tweaks.ps1", "security-tweaks.ps1", "beauty-tweaks.ps1")
$allOk = $true

foreach ($f in $files) {
    $p = Join-Path $scriptRoot $f
    if (Test-Path $p) {
        Write-Host "[OK] $f" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $f" -ForegroundColor Red
        $allOk = $false
    }
}

if ($allOk) {
    Write-Host "`nAll scripts found! Ready to run." -ForegroundColor Green
    Write-Host "Run: .\optimize-windows.ps1 -All (as Administrator)" -ForegroundColor Yellow
} else {
    Write-Host "`nSome files missing!" -ForegroundColor Red
}

