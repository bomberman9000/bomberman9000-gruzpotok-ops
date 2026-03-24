# Dark Theme with White Text on Black Background
# Perfect dark theme setup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dark Theme: White Text on Black" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Enable dark theme
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

Write-Host "[1/3] Enabling dark theme..." -ForegroundColor Yellow
Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $themeKey -Name "EnableTransparency" -Value 1 -ErrorAction SilentlyContinue
Write-Host "  [OK] Dark theme enabled" -ForegroundColor Green

# Set colors: WHITE text on BLACK background
Write-Host ""
Write-Host "[2/3] Setting colors (white text on black)..." -ForegroundColor Yellow
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# WHITE text on BLACK background
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Window" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "20 20 20" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonFace" -Value "40 40 40" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonHighlight" -Value "70 130 180" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Highlight" -Value "0 120 215" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "HighlightText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "GrayText" -Value "128 128 128" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "InfoText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "InfoWindow" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Scrollbar" -Value "40 40 40" -ErrorAction SilentlyContinue

Write-Host "  [OK] White text on black background configured" -ForegroundColor Green

# Fix Explorer
Write-Host ""
Write-Host "[3/3] Fixing Explorer..." -ForegroundColor Yellow
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

Set-ItemProperty -Path $explorerKey -Name "ListviewAlphaSelect" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ListviewShadow" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ShowInfoTip" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Explorer configured" -ForegroundColor Green

# Restart Explorer
Write-Host ""
Write-Host "Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process "explorer.exe"
Write-Host "  [OK] Explorer restarted" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dark Theme Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Theme: DARK" -ForegroundColor Yellow
Write-Host "Text: WHITE on BLACK background" -ForegroundColor White
Write-Host "Perfect contrast!" -ForegroundColor Green
Write-Host ""
Write-Host "If text is not visible, RESTART your computer!" -ForegroundColor Yellow
Write-Host ""









