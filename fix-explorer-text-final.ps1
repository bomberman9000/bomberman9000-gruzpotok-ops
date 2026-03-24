# Final Fix for Explorer Text Visibility
# Mixed mode: Light Explorer, Dark Apps

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Final Fix: Explorer Text Visibility" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Using MIXED MODE:" -ForegroundColor Yellow
Write-Host "  - Light theme for Explorer (text visible)" -ForegroundColor White
Write-Host "  - Dark theme for apps (if you want)" -ForegroundColor White
Write-Host ""

# Set mixed mode
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

# Light theme for Windows (Explorer)
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 1 -ErrorAction SilentlyContinue

# Ask user preference for apps
Write-Host "Choose theme for applications:" -ForegroundColor Yellow
Write-Host "  1. Light (recommended for visibility)" -ForegroundColor White
Write-Host "  2. Dark" -ForegroundColor White
$choice = Read-Host "Enter choice (1 or 2)"

if ($choice -eq "2") {
    Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
    Write-Host "[OK] Dark theme for apps" -ForegroundColor Green
} else {
    Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 1 -ErrorAction SilentlyContinue
    Write-Host "[OK] Light theme for apps" -ForegroundColor Green
}

# Fix colors - ensure black text on white background
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# Light theme colors - BLACK text on WHITE background
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Window" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonText" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonFace" -Value "240 240 240" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Highlight" -Value "0 120 215" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "HighlightText" -Value "255 255 255" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[OK] Colors set to light theme (black text on white)" -ForegroundColor Green

# Fix Explorer settings
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

Set-ItemProperty -Path $explorerKey -Name "ListviewAlphaSelect" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ShowInfoTip" -Value 1 -ErrorAction SilentlyContinue

Write-Host "[OK] Explorer settings fixed" -ForegroundColor Green

# Restart Explorer
Write-Host ""
Write-Host "Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process "explorer.exe"
Write-Host "[OK] Explorer restarted" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Explorer now uses LIGHT theme:" -ForegroundColor Yellow
Write-Host "  ✓ Black text on white background" -ForegroundColor White
Write-Host "  ✓ Text should be clearly visible" -ForegroundColor White
Write-Host ""
Write-Host "If still not visible, RESTART your computer!" -ForegroundColor Red
Write-Host ""









