# Quick Fix Explorer Colors - No Admin
# Fixes text visibility in Explorer

Write-Host "Fixing Explorer colors..." -ForegroundColor Cyan
Write-Host ""

# Option 1: Switch to light theme (if dark theme causes issues)
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

Write-Host "Current theme:" -ForegroundColor Yellow
$current = Get-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -ErrorAction SilentlyContinue
if ($current.AppsUseLightTheme -eq 0) {
    Write-Host "  Dark theme is active" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Switching to light theme for better visibility..." -ForegroundColor Yellow
    Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 1 -ErrorAction SilentlyContinue
    Write-Host "[OK] Switched to light theme" -ForegroundColor Green
} else {
    Write-Host "  Light theme is active" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Theme is already light. Fixing colors..." -ForegroundColor Yellow
    
    # Ensure proper colors
    Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 1 -ErrorAction SilentlyContinue
    Write-Host "[OK] Colors fixed" -ForegroundColor Green
}

# Fix color profile
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# Set proper colors for light theme
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Window" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "0 0 0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "255 255 255" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "explorer.exe"
Write-Host "[OK] Explorer restarted" -ForegroundColor Green

Write-Host ""
Write-Host "Colors fixed! Text should be visible now." -ForegroundColor Green
Write-Host ""
Write-Host "If you want dark theme back:" -ForegroundColor Yellow
Write-Host "  Settings → Personalization → Colors → Dark" -ForegroundColor White
Write-Host ""









