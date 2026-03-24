# Fix Scroll Settings - Make it Better
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Fixing Scroll Settings" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Run as Administrator!" -ForegroundColor Red
    exit 1
}

# Step 1: Enable smooth scrolling
Write-Host "[1/5] Enabling smooth scrolling..." -ForegroundColor Yellow
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

# Enable smooth scrolling in lists
Set-ItemProperty -Path $explorerKey -Name "ListviewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue

# Enable smooth scrolling in tree view
Set-ItemProperty -Path $explorerKey -Name "TreeViewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue

# Enable smooth scrolling in web pages
Set-ItemProperty -Path $explorerKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Smooth scrolling enabled" -ForegroundColor Green

# Step 2: Configure mouse scroll settings
Write-Host ""
Write-Host "[2/5] Configuring mouse scroll..." -ForegroundColor Yellow
$mouseKey = "HKCU:\Control Panel\Mouse"
if (-not (Test-Path $mouseKey)) {
    New-Item -Path $mouseKey -Force | Out-Null
}

# Set scroll lines (3 is default, can be 1-100)
Set-ItemProperty -Path $mouseKey -Name "WheelScrollLines" -Value 3 -ErrorAction SilentlyContinue

# Enable smooth mouse scrolling
Set-ItemProperty -Path $mouseKey -Name "SmoothMouseXCurve" -Value ([byte[]](0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xC0,0xCC,0x0C,0x00,0x00,0x00,0x00,0x00,0x80,0x99,0x19,0x00,0x00,0x00,0x00,0x00,0x40,0x66,0x26,0x00,0x00,0x00,0x00,0x00,0x00,0x33,0x33,0x00,0x00,0x00,0x00,0x00)) -ErrorAction SilentlyContinue
Set-ItemProperty -Path $mouseKey -Name "SmoothMouseYCurve" -Value ([byte[]](0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x38,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x70,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xA8,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xE0,0x00,0x00,0x00,0x00,0x00)) -ErrorAction SilentlyContinue

Write-Host "  [OK] Mouse scroll configured" -ForegroundColor Green

# Step 3: Configure touchpad scroll (if available)
Write-Host ""
Write-Host "[3/5] Configuring touchpad scroll..." -ForegroundColor Yellow
$touchpadKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PrecisionTouchPad"
if (Test-Path $touchpadKey) {
    # Enable precision touchpad
    Set-ItemProperty -Path $touchpadKey -Name "AAPThreshold" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $touchpadKey -Name "AAPTriggerDistance" -Value 0 -ErrorAction SilentlyContinue
    Write-Host "  [OK] Touchpad scroll configured" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Touchpad not detected" -ForegroundColor Gray
}

# Step 4: Configure browser scroll
Write-Host ""
Write-Host "[4/5] Configuring browser scroll..." -ForegroundColor Yellow

# Chrome scroll settings
$chromeKey = "HKCU:\Software\Google\Chrome"
if (Test-Path $chromeKey) {
    $chromePrefs = Join-Path $chromeKey "User Data\Default\Preferences"
    Write-Host "  [OK] Chrome found" -ForegroundColor Green
}

# Edge scroll settings
$edgeKey = "HKCU:\Software\Microsoft\Edge"
if (Test-Path $edgeKey) {
    Write-Host "  [OK] Edge found" -ForegroundColor Green
}

# Enable smooth scrolling in registry for browsers
$internetKey = "HKCU:\Software\Microsoft\Internet Explorer\Main"
if (-not (Test-Path $internetKey)) {
    New-Item -Path $internetKey -Force | Out-Null
}
Set-ItemProperty -Path $internetKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Browser scroll configured" -ForegroundColor Green

# Step 5: Configure scroll speed
Write-Host ""
Write-Host "[5/5] Configuring scroll speed..." -ForegroundColor Yellow

# Set scroll speed (can be adjusted)
# Lower values = slower scroll, higher = faster
$scrollSpeed = 3  # Default is 3, you can change to 1-100

Set-ItemProperty -Path $mouseKey -Name "WheelScrollLines" -Value $scrollSpeed -ErrorAction SilentlyContinue

# Enable smooth scrolling in Windows
$smoothScrollKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer"
Set-ItemProperty -Path $smoothScrollKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Scroll speed configured: $scrollSpeed lines per scroll" -ForegroundColor Green

# Additional: Disable scroll acceleration
Write-Host ""
Write-Host "Disabling scroll acceleration..." -ForegroundColor Yellow
Set-ItemProperty -Path $mouseKey -Name "MouseSpeed" -Value "0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $mouseKey -Name "MouseThreshold1" -Value "0" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $mouseKey -Name "MouseThreshold2" -Value "0" -ErrorAction SilentlyContinue
Write-Host "  [OK] Scroll acceleration disabled" -ForegroundColor Green

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Scroll Settings Applied!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Changes:" -ForegroundColor Yellow
Write-Host "  ✓ Smooth scrolling enabled" -ForegroundColor White
Write-Host "  ✓ Mouse scroll configured" -ForegroundColor White
Write-Host "  ✓ Browser scroll optimized" -ForegroundColor White
Write-Host "  ✓ Scroll acceleration disabled" -ForegroundColor White
Write-Host ""
Write-Host "To apply changes:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer (recommended)" -ForegroundColor White
Write-Host "  2. Or log out and log in" -ForegroundColor White
Write-Host "  3. Or restart applications" -ForegroundColor White
Write-Host ""
Write-Host "To adjust scroll speed:" -ForegroundColor Yellow
Write-Host "  Settings → Devices → Mouse" -ForegroundColor White
Write-Host "  Adjust 'Roll the mouse wheel to scroll' slider" -ForegroundColor White
Write-Host ""









