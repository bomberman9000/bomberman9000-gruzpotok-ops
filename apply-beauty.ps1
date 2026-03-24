# Apply Beautiful Windows Theme - Force
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Applying Beautiful Windows Theme" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Dark Theme
Write-Host "[1/8] Enabling dark theme..." -ForegroundColor Yellow
$darkThemeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $darkThemeKey)) {
    New-Item -Path $darkThemeKey -Force | Out-Null
}
Set-ItemProperty -Path $darkThemeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $darkThemeKey -Name "SystemUsesLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $darkThemeKey -Name "EnableTransparency" -Value 1 -ErrorAction SilentlyContinue
Write-Host "  [OK] Dark theme enabled" -ForegroundColor Green

# Accent Color
Write-Host ""
Write-Host "[2/8] Setting accent color..." -ForegroundColor Yellow
$accentKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
if (-not (Test-Path $accentKey)) {
    New-Item -Path $accentKey -Force | Out-Null
}
Set-ItemProperty -Path $accentKey -Name "AccentColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $accentKey -Name "StartColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue
Write-Host "  [OK] Accent color set" -ForegroundColor Green

# Taskbar
Write-Host ""
Write-Host "[3/8] Optimizing taskbar..." -ForegroundColor Yellow
$taskbarKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $taskbarKey)) {
    New-Item -Path $taskbarKey -Force | Out-Null
}
Set-ItemProperty -Path $taskbarKey -Name "TaskbarSmallIcons" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "TaskbarGlomLevel" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "SearchboxTaskbarMode" -Value 0 -ErrorAction SilentlyContinue
Write-Host "  [OK] Taskbar optimized" -ForegroundColor Green

# Start Menu
Write-Host ""
Write-Host "[4/8] Optimizing Start Menu..." -ForegroundColor Yellow
Set-ItemProperty -Path $taskbarKey -Name "Start_TrackProgs" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "Start_NotifyNewApps" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "Start_JumpListItems" -Value 10 -ErrorAction SilentlyContinue
Write-Host "  [OK] Start Menu optimized" -ForegroundColor Green

# File Explorer
Write-Host ""
Write-Host "[5/8] Optimizing File Explorer..." -ForegroundColor Yellow
Set-ItemProperty -Path $taskbarKey -Name "HideFileExt" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "Hidden" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "AutoCheckSelect" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "FullPath" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "ShowRecent" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $taskbarKey -Name "ShowFrequent" -Value 0 -ErrorAction SilentlyContinue
Write-Host "  [OK] File Explorer optimized" -ForegroundColor Green

# Disable Ads
Write-Host ""
Write-Host "[6/8] Disabling ads..." -ForegroundColor Yellow
$startMenuAds = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
if (Test-Path $startMenuAds) {
    Set-ItemProperty -Path $startMenuAds -Name "SystemPaneSuggestionsEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "SoftLandingEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "RotatingLockScreenEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "RotatingLockScreenOverlayEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-338393Enabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-353694Enabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-353696Enabled" -Value 0 -ErrorAction SilentlyContinue
    Write-Host "  [OK] Ads disabled" -ForegroundColor Green
}

# Visual Effects
Write-Host ""
Write-Host "[7/8] Enabling visual effects..." -ForegroundColor Yellow
$visualKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
if (-not (Test-Path $visualKey)) {
    New-Item -Path $visualKey -Force | Out-Null
}
Set-ItemProperty -Path $visualKey -Name "ListviewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $visualKey -Name "AnimateMinMax" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $visualKey -Name "WindowShadow" -Value 1 -ErrorAction SilentlyContinue
Write-Host "  [OK] Visual effects enabled" -ForegroundColor Green

# Font Smoothing
Write-Host ""
Write-Host "[8/8] Configuring font smoothing..." -ForegroundColor Yellow
$displayKey = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $displayKey -Name "FontSmoothing" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $displayKey -Name "FontSmoothingType" -Value 2 -ErrorAction SilentlyContinue
Write-Host "  [OK] Font smoothing configured" -ForegroundColor Green

# Restart Explorer
Write-Host ""
Write-Host "Restarting Explorer to apply changes..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "explorer.exe"
Write-Host "  [OK] Explorer restarted" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Beautiful Theme Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Changes applied:" -ForegroundColor Yellow
Write-Host "  ✓ Dark theme enabled" -ForegroundColor White
Write-Host "  ✓ Accent color set" -ForegroundColor White
Write-Host "  ✓ Taskbar optimized" -ForegroundColor White
Write-Host "  ✓ Start Menu optimized" -ForegroundColor White
Write-Host "  ✓ File Explorer improved" -ForegroundColor White
Write-Host "  ✓ Ads disabled" -ForegroundColor White
Write-Host "  ✓ Visual effects enabled" -ForegroundColor White
Write-Host ""
Write-Host "If changes are not visible:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer" -ForegroundColor White
Write-Host "  2. Or log out and log in" -ForegroundColor White
Write-Host ""

