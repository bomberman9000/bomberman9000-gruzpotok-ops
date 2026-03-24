# Enable VPN Autostart - Quick
# No admin required for enabling existing task

Write-Host "Enabling Hysteria2 autostart..." -ForegroundColor Cyan
Write-Host ""

$taskName = "Hysteria2-Startup"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($task) {
    if ($task.State -eq "Ready" -and $task.Settings.Enabled) {
        Write-Host "[OK] Autostart is already enabled!" -ForegroundColor Green
        Write-Host "  Task: $taskName" -ForegroundColor Gray
        Write-Host "  State: $($task.State)" -ForegroundColor Gray
        Write-Host "  Enabled: $($task.Settings.Enabled)" -ForegroundColor Gray
    } else {
        Write-Host "Enabling task..." -ForegroundColor Yellow
        Enable-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Write-Host "[OK] Autostart enabled!" -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] Task not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Create it first:" -ForegroundColor Yellow
    Write-Host "  .\setup-hysteria2-autostart.ps1" -ForegroundColor White
    Write-Host "  (Run as Administrator)" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "Hysteria2 will start automatically on login!" -ForegroundColor Green
Write-Host ""
Write-Host "To test: Log out and log in again" -ForegroundColor Yellow
Write-Host ""









