# Force Theme Change - Multiple Methods
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Force Theme Change" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Method 1: Registry - Force dark theme
Write-Host "[1/4] Setting dark theme in registry..." -ForegroundColor Yellow
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $themeKey)) {
    New-Item -Path $themeKey -Force | Out-Null
}

Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $themeKey -Name "EnableTransparency" -Value 1 -Type DWord -Force

Write-Host "  [OK] Registry updated" -ForegroundColor Green

# Method 2: System colors - Force white text
Write-Host ""
Write-Host "[2/4] Setting system colors..." -ForegroundColor Yellow
$colorKey = "HKCU:\Control Panel\Colors"
if (-not (Test-Path $colorKey)) {
    New-Item -Path $colorKey -Force | Out-Null
}

# Force white text on black
Set-ItemProperty -Path $colorKey -Name "WindowText" -Value "255 255 255" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "Window" -Value "0 0 0" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "MenuText" -Value "255 255 255" -Type String -Force
Set-ItemProperty -Path $colorKey -Name "Menu" -Value "20 20 20" -Type String -Force

Write-Host "  [OK] Colors set" -ForegroundColor Green

# Method 3: Use Windows API via rundll32
Write-Host ""
Write-Host "[3/4] Applying theme via Windows API..." -ForegroundColor Yellow
try {
    # Refresh theme
    rundll32.exe uxtheme.dll,#64 | Out-Null
    Write-Host "  [OK] Theme refreshed" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not refresh theme" -ForegroundColor Yellow
}

# Method 4: Restart DWM and Explorer
Write-Host ""
Write-Host "[4/4] Restarting DWM and Explorer..." -ForegroundColor Yellow
try {
    # Restart DWM (Desktop Window Manager)
    Stop-Process -Name "dwm" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Restart Explorer
    Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Start-Process "explorer.exe"
    
    Write-Host "  [OK] DWM and Explorer restarted" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Could not restart DWM" -ForegroundColor Yellow
    # Just restart Explorer
    Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Start-Process "explorer.exe"
    Write-Host "  [OK] Explorer restarted" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Theme Change Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "CRITICAL: RESTART YOUR COMPUTER NOW!" -ForegroundColor Red
Write-Host "This is the only way to ensure all changes apply!" -ForegroundColor Yellow
Write-Host ""









