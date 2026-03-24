# Quick Scroll Fix - No Admin Required
# User-level settings only

Write-Host "Fixing scroll settings..." -ForegroundColor Cyan
Write-Host ""

# Enable smooth scrolling
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $explorerKey)) {
    New-Item -Path $explorerKey -Force | Out-Null
}

Set-ItemProperty -Path $explorerKey -Name "ListviewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "TreeViewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue

Write-Host "[OK] Smooth scrolling enabled" -ForegroundColor Green

# Configure mouse scroll
$mouseKey = "HKCU:\Control Panel\Mouse"
if (-not (Test-Path $mouseKey)) {
    New-Item -Path $mouseKey -Force | Out-Null
}

# Set scroll lines (3 = default, change if needed)
Set-ItemProperty -Path $mouseKey -Name "WheelScrollLines" -Value 3 -ErrorAction SilentlyContinue

Write-Host "[OK] Mouse scroll configured" -ForegroundColor Green

# Browser scroll
$internetKey = "HKCU:\Software\Microsoft\Internet Explorer\Main"
if (-not (Test-Path $internetKey)) {
    New-Item -Path $internetKey -Force | Out-Null
}
Set-ItemProperty -Path $internetKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue

Write-Host "[OK] Browser scroll configured" -ForegroundColor Green

Write-Host ""
Write-Host "Settings applied!" -ForegroundColor Green
Write-Host ""
Write-Host "To adjust scroll speed:" -ForegroundColor Yellow
Write-Host "  Settings → Devices → Mouse" -ForegroundColor White
Write-Host "  Adjust scroll wheel settings" -ForegroundColor White
Write-Host ""
Write-Host "Restart applications to see changes." -ForegroundColor Cyan
Write-Host ""









