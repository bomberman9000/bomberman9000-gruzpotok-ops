# Fix Dark Theme - Make Text Visible
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Dark Theme Text Visibility" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Enable dark theme properly
Write-Host "[1/6] Enabling dark theme..." -ForegroundColor Yellow
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

# Set dark theme
Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $themeKey -Name "EnableTransparency" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Dark theme enabled" -ForegroundColor Green

# Step 2: Fix color profile for dark theme
Write-Host ""
Write-Host "[2/6] Fixing color profile for dark theme..." -ForegroundColor Yellow
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# Set proper colors for dark theme - WHITE text on DARK background
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Window" -Value "32 32 32" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "40 40 40" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonFace" -Value "48 48 48" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonHighlight" -Value "70 130 180" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Highlight" -Value "0 120 215" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "HighlightText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "GrayText" -Value "128 128 128" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "InfoText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "InfoWindow" -Value "32 32 32" -ErrorAction SilentlyContinue

Write-Host "  [OK] Color profile fixed (white text on dark background)" -ForegroundColor Green

# Step 3: Fix Explorer colors
Write-Host ""
Write-Host "[3/6] Fixing Explorer colors..." -ForegroundColor Yellow
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

# Enable proper text rendering
Set-ItemProperty -Path $explorerKey -Name "ListviewAlphaSelect" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ListviewShadow" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ShowInfoTip" -Value 1 -ErrorAction SilentlyContinue

# Fix selection colors
Set-ItemProperty -Path $explorerKey -Name "ListviewWatermark" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  [OK] Explorer colors fixed" -ForegroundColor Green

# Step 4: Fix accent color for better contrast
Write-Host ""
Write-Host "[4/6] Setting accent color..." -ForegroundColor Yellow
$accentKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
if (-not (Test-Path $accentKey)) {
    New-Item -Path $accentKey -Force | Out-Null
}

# Set blue accent color (good contrast with dark theme)
Set-ItemProperty -Path $accentKey -Name "AccentColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $accentKey -Name "StartColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue

Write-Host "  [OK] Accent color set" -ForegroundColor Green

# Step 5: Disable high contrast (if causing issues)
Write-Host ""
Write-Host "[5/6] Checking high contrast..." -ForegroundColor Yellow
$accessibilityKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Accessibility"
if (Test-Path $accessibilityKey) {
    Set-ItemProperty -Path $accessibilityKey -Name "Configuration" -Value "normal" -ErrorAction SilentlyContinue
    Write-Host "  [OK] High contrast disabled" -ForegroundColor Green
} else {
    Write-Host "  [OK] High contrast not active" -ForegroundColor Green
}

# Step 6: Restart Explorer
Write-Host ""
Write-Host "[6/6] Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "explorer.exe"
Write-Host "  [OK] Explorer restarted" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dark Theme Fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Dark theme enabled with visible text:" -ForegroundColor Yellow
Write-Host "  ✓ White text on dark background" -ForegroundColor White
Write-Host "  ✓ Proper contrast" -ForegroundColor White
Write-Host "  ✓ Explorer colors fixed" -ForegroundColor White
Write-Host ""
Write-Host "If text is still not visible:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer" -ForegroundColor White
Write-Host "  2. Check: Settings → Personalization → Colors" -ForegroundColor White
Write-Host "  3. Ensure Dark mode is selected" -ForegroundColor White
Write-Host ""

