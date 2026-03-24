# Add Kaspersky exclusions via Registry
# This script adds exclusions to Kaspersky using Registry

Write-Host "Adding Kaspersky exclusions..." -ForegroundColor Cyan
Write-Host ""

# Kaspersky Registry path
$kasperskyPath = "HKLM:\SOFTWARE\WOW6432Node\KasperskyLab\AVP*\Data\Exclusions"

# Check if Kaspersky is installed
$kasperskyInstalled = Test-Path "HKLM:\SOFTWARE\WOW6432Node\KasperskyLab"

if (-not $kasperskyInstalled) {
    Write-Host "[WARN] Kaspersky registry path not found" -ForegroundColor Yellow
    Write-Host "You may need to add exclusions manually" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Cyan
    Write-Host "1. Open Kaspersky" -ForegroundColor White
    Write-Host "2. Settings → Advanced → Threats and Exclusions" -ForegroundColor White
    Write-Host "3. Configure Exclusions" -ForegroundColor White
    Write-Host "4. Add these paths:" -ForegroundColor White
    Write-Host "   - C:\Users\Shata\AppData\Local\Programs\cursor\*" -ForegroundColor Gray
    Write-Host "   - C:\Users\Shata\project\*" -ForegroundColor Gray
    exit 0
}

# Exclusions to add
$exclusions = @(
    "C:\Users\Shata\AppData\Local\Programs\cursor\*",
    "C:\Users\Shata\project\*",
    "C:\Users\Shata\AppData\Local\Programs\cursor\Cursor.exe"
)

Write-Host "[INFO] Kaspersky found" -ForegroundColor Green
Write-Host "[INFO] Note: Registry method may not work for all Kaspersky versions" -ForegroundColor Yellow
Write-Host ""
Write-Host "RECOMMENDED: Add exclusions manually in Kaspersky settings" -ForegroundColor Cyan
Write-Host ""
Write-Host "Paths to exclude:" -ForegroundColor Cyan
foreach ($exclusion in $exclusions) {
    Write-Host "  - $exclusion" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Press any key to open Kaspersky settings..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Try to open Kaspersky settings (if possible)
try {
    Start-Process "kav.exe" -ArgumentList "/settings" -ErrorAction SilentlyContinue
} catch {
    Write-Host "[INFO] Could not open Kaspersky automatically" -ForegroundColor Yellow
    Write-Host "Please open Kaspersky manually and add exclusions" -ForegroundColor Yellow
}





