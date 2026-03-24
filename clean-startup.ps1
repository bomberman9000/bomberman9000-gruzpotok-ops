# Clean Startup - Remove Unnecessary Programs
# Run as Administrator for full cleanup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Clean Startup Programs" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Programs to remove from startup (obviously unnecessary)
$programsToRemove = @(
    "MicrosoftEdgeAutoLaunch",
    "YandexBrowserAutoLaunch",
    "Skydimo",
    "Dark Project"
)

# Registry startup
Write-Host "[1/2] Cleaning registry startup..." -ForegroundColor Yellow
$registryStartup = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue

if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    $removed = 0
    
    foreach ($key in $regKeys) {
        $shouldRemove = $false
        foreach ($remove in $programsToRemove) {
            if ($key.Name -like "*$remove*") {
                $shouldRemove = $true
                break
            }
        }
        
        if ($shouldRemove) {
            try {
                Write-Host "  Removing: $($key.Name)" -ForegroundColor Gray
                Remove-ItemProperty -Path $registryStartup -Name $key.Name -ErrorAction SilentlyContinue
                $removed++
            } catch {
                Write-Host "  [WARN] Could not remove: $($key.Name)" -ForegroundColor Yellow
            }
        }
    }
    
    if ($removed -gt 0) {
        Write-Host "  [OK] Removed $removed programs from startup" -ForegroundColor Green
    } else {
        Write-Host "  [OK] No unnecessary programs found" -ForegroundColor Green
    }
} else {
    Write-Host "  [OK] No registry startup items" -ForegroundColor Green
}

# Show remaining startup
Write-Host ""
Write-Host "[2/2] Remaining startup programs:" -ForegroundColor Yellow
Write-Host ""

$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    if ($regKeys) {
        foreach ($key in $regKeys) {
            Write-Host "  - $($key.Name): $($key.Value)" -ForegroundColor White
        }
    } else {
        Write-Host "  (none)" -ForegroundColor Gray
    }
} else {
    Write-Host "  (none)" -ForegroundColor Gray
}

# Show important programs that should stay
Write-Host ""
Write-Host "Important programs (kept):" -ForegroundColor Cyan
Write-Host "  - Hysteria2 (VPN)" -ForegroundColor Green
Write-Host "  - Docker Desktop (if you use it)" -ForegroundColor Yellow
Write-Host "  - OpenVPN-GUI (if you use it)" -ForegroundColor Yellow
Write-Host ""

Write-Host "To remove more programs manually:" -ForegroundColor Yellow
Write-Host "  Task Manager → Startup tab" -ForegroundColor White
Write-Host "  Or: Settings → Apps → Startup" -ForegroundColor White
Write-Host ""









