# Apply Theme via Windows Settings
# Opens settings and applies theme

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Apply Dark Theme via Settings" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Opening Windows Settings..." -ForegroundColor Yellow
Start-Process "ms-settings:personalization-colors"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MANUAL STEPS REQUIRED" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "In the Settings window that opened:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Choose 'Dark' mode" -ForegroundColor White
Write-Host "   OR" -ForegroundColor Gray
Write-Host "2. Choose 'Custom' and set:" -ForegroundColor White
Write-Host "   - Windows mode: Dark" -ForegroundColor Gray
Write-Host "   - App mode: Dark" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Click outside the window to save" -ForegroundColor White
Write-Host ""
Write-Host "This will apply the theme correctly!" -ForegroundColor Green
Write-Host ""









