# Final Fix for Colors - Force Light Theme
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FINAL FIX: Force Light Theme" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

Write-Host "This will FORCE light theme to fix black text on black background" -ForegroundColor Yellow
Write-Host ""

# Step 1: Force light theme
Write-Host "[1/4] Forcing light theme..." -ForegroundColor Yellow
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 1 -Type DWord -Force
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 1 -Type DWord -Force
Set-ItemProperty -Path $themeKey -Name "EnableTransparency" -Value 0 -Type DWord -Force

Write-Host "  [OK] Light theme forced" -ForegroundColor Green

# Step 2: Force light colors
Write-Host ""
Write-Host "[2/4] Forcing light colors..." -ForegroundColor Yellow
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# BLACK text on WHITE background
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "0 0 0" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "Window" -Value "255 255 255" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "0 0 0" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "255 255 255" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "ButtonText" -Value "0 0 0" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "ButtonFace" -Value "240 240 240" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "Highlight" -Value "0 120 215" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "HighlightText" -Value "255 255 255" -Type String -Force

Write-Host "  [OK] Light colors forced (black text on white)" -ForegroundColor Green

# Step 3: Disable high contrast
Write-Host ""
Write-Host "[3/4] Disabling high contrast..." -ForegroundColor Yellow
$accessibilityKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Accessibility"
if (Test-Path $accessibilityKey) {
    Set-ItemProperty -Path $accessibilityKey -Name "Configuration" -Value "normal" -Type String -Force -ErrorAction SilentlyContinue
}
Write-Host "  [OK] High contrast disabled" -ForegroundColor Green

# Step 4: Restart DWM and Explorer
Write-Host ""
Write-Host "[4/4] Restarting DWM and Explorer..." -ForegroundColor Yellow
try {
    Stop-Process -Name "dwm" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} catch {
    Write-Host "  [WARN] Could not restart DWM" -ForegroundColor Yellow
}

Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process "explorer.exe"

Write-Host "  [OK] DWM and Explorer restarted" -ForegroundColor Green

# Open settings
Write-Host ""
Write-Host "Opening Windows Settings..." -ForegroundColor Yellow
Start-Process "ms-settings:personalization-colors"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CRITICAL: RESTART YOUR COMPUTER!" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Changes applied, but you MUST restart to see them!" -ForegroundColor Yellow
Write-Host ""
Write-Host "In the Settings window that opened:" -ForegroundColor Yellow
Write-Host "  1. Select 'Light' mode" -ForegroundColor White
Write-Host "  2. Then RESTART your computer" -ForegroundColor White
Write-Host ""
Write-Host "This is the ONLY way to fix the color issue!" -ForegroundColor Red
Write-Host ""









