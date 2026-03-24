# Fix Explorer Colors - Make Text Visible
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Explorer Colors" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Fix theme settings
Write-Host "[1/5] Fixing theme settings..." -ForegroundColor Yellow
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

# Set proper theme - if dark theme, ensure proper contrast
$currentTheme = Get-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -ErrorAction SilentlyContinue
if ($currentTheme.AppsUseLightTheme -eq 0) {
    Write-Host "  [INFO] Dark theme detected" -ForegroundColor Gray
    Write-Host "  [INFO] Ensuring proper contrast..." -ForegroundColor Gray
}

# Keep dark theme but fix colors
Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  [OK] Theme settings fixed" -ForegroundColor Green

# Step 2: Fix Explorer color scheme
Write-Host ""
Write-Host "[2/5] Fixing Explorer color scheme..." -ForegroundColor Yellow
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

# Enable proper color display
Set-ItemProperty -Path $explorerKey -Name "ListviewAlphaSelect" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ListviewShadow" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "TaskbarGlomLevel" -Value 0 -ErrorAction SilentlyContinue

# Fix text color issues
Set-ItemProperty -Path $explorerKey -Name "ShowInfoTip" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "Hidden" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ShowSuperHidden" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  [OK] Explorer color scheme fixed" -ForegroundColor Green

# Step 3: Fix high contrast (if enabled)
Write-Host ""
Write-Host "[3/5] Checking high contrast..." -ForegroundColor Yellow
$highContrast = Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes" -Name "LastTheme" -ErrorAction SilentlyContinue
if ($highContrast) {
    Write-Host "  [INFO] High contrast theme found" -ForegroundColor Gray
}

# Disable problematic high contrast
$accessibilityKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Accessibility"
if (Test-Path $accessibilityKey) {
    Set-ItemProperty -Path $accessibilityKey -Name "Configuration" -Value "normal" -ErrorAction SilentlyContinue
}

Write-Host "  [OK] High contrast checked" -ForegroundColor Green

# Step 4: Fix color profile
Write-Host ""
Write-Host "[4/5] Fixing color profile..." -ForegroundColor Yellow
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# Set proper text colors for dark theme
# Window text: white for dark theme
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Window" -Value "32 32 32" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "32 32 32" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonText" -Value "255 255 255" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $colorKey -Name "ButtonFace" -Value "48 48 48" -ErrorAction SilentlyContinue

Write-Host "  [OK] Color profile fixed" -ForegroundColor Green

# Step 5: Reset Explorer
Write-Host ""
Write-Host "[5/5] Restarting Explorer..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "explorer.exe"
Write-Host "  [OK] Explorer restarted" -ForegroundColor Green

# Alternative: Switch to light theme if dark doesn't work
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Colors Fixed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If text is still not visible:" -ForegroundColor Yellow
Write-Host "  Option 1: Switch to light theme" -ForegroundColor White
Write-Host "    Settings → Personalization → Colors" -ForegroundColor Gray
Write-Host "    Set to Light mode" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option 2: Adjust contrast" -ForegroundColor White
Write-Host "    Settings → Ease of Access → High contrast" -ForegroundColor Gray
Write-Host "    Try different themes" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option 3: Run this script again" -ForegroundColor White
Write-Host "    .\fix-explorer-colors.ps1" -ForegroundColor Gray
Write-Host ""









