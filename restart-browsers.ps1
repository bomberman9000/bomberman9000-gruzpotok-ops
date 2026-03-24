# Restart All Browsers
# This will close and you need to reopen them

Write-Host "Restarting browsers..." -ForegroundColor Cyan
Write-Host ""

$browsers = @(
    @{Name="chrome"; Display="Google Chrome"},
    @{Name="msedge"; Display="Microsoft Edge"},
    @{Name="firefox"; Display="Mozilla Firefox"},
    @{Name="opera"; Display="Opera"},
    @{Name="brave"; Display="Brave Browser"}
)

$found = $false
foreach ($browser in $browsers) {
    $processes = Get-Process -Name $browser.Name -ErrorAction SilentlyContinue
    if ($processes) {
        $found = $true
        Write-Host "Stopping $($browser.Display)..." -ForegroundColor Yellow
        Stop-Process -Name $browser.Name -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] $($browser.Display) stopped" -ForegroundColor Green
    }
}

if (-not $found) {
    Write-Host "No browsers found running" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "All browsers stopped!" -ForegroundColor Green
    Write-Host "Now open your browser again - it will use the proxy." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Proxy settings:" -ForegroundColor Cyan
Write-Host "  HTTP: 127.0.0.1:8080" -ForegroundColor White
Write-Host "  SOCKS5: 127.0.0.1:1080" -ForegroundColor White
Write-Host ""









