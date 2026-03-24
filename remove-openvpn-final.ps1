# Remove OpenVPN - Final Script
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Удаление OpenVPN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Требуются права администратора!" -ForegroundColor Red
    Write-Host "[INFO] Запустите PowerShell от имени администратора" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Правильная команда:" -ForegroundColor Cyan
    Write-Host '  & "MsiExec.exe" /X"{86469515-EF76-40E9-9F71-732C6B17888C}" /S' -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}

# Find OpenVPN
Write-Host "[1/3] Поиск OpenVPN..." -ForegroundColor Yellow
$openvpn = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*OpenVPN*" }

if (-not $openvpn) {
    Write-Host "  [OK] OpenVPN не найден (уже удален)" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "OpenVPN уже удален!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    pause
    exit 0
}

Write-Host "  Найдено: $($openvpn.DisplayName)" -ForegroundColor Green
Write-Host "  GUID: {86469515-EF76-40E9-9F71-732C6B17888C}" -ForegroundColor Gray
Write-Host ""

# Stop OpenVPN services
Write-Host "[2/3] Остановка служб OpenVPN..." -ForegroundColor Yellow
$services = @("OpenVPNService", "OpenVPNServiceInteractive", "openvpnserv", "openvpnserv2")
foreach ($serviceName in $services) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service) {
        try {
            if ($service.Status -eq "Running") {
                Write-Host "  Останавливаю: $serviceName" -ForegroundColor Gray
                Stop-Service -Name $serviceName -Force -ErrorAction Stop
                Write-Host "  [OK] Служба остановлена" -ForegroundColor Green
            }
        } catch {
            Write-Host "  [WARN] Не удалось остановить: $serviceName" -ForegroundColor Yellow
        }
    }
}

# Stop processes
$processes = Get-Process | Where-Object { $_.ProcessName -like "*openvpn*" }
if ($processes) {
    foreach ($proc in $processes) {
        try {
            Write-Host "  Останавливаю процесс: $($proc.ProcessName)" -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
        } catch {
            Write-Host "  [WARN] Не удалось остановить процесс" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# Uninstall OpenVPN
Write-Host "[3/3] Удаление OpenVPN..." -ForegroundColor Yellow
$guid = "{86469515-EF76-40E9-9F71-732C6B17888C}"

try {
    Write-Host "  Запускаю удаление..." -ForegroundColor Gray
    $process = Start-Process -FilePath "MsiExec.exe" -ArgumentList "/X$guid", "/S", "/NORESTART", "/L*v", "$env:TEMP\openvpn_uninstall.log" -Wait -NoNewWindow -PassThru
    
    Start-Sleep -Seconds 3
    
    # Check if removed
    $check = Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*OpenVPN*" }
    
    if (-not $check) {
        Write-Host "  [OK] OpenVPN успешно удален!" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] OpenVPN все еще установлен" -ForegroundColor Yellow
        Write-Host "  [INFO] Проверьте лог: $env:TEMP\openvpn_uninstall.log" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [ERROR] Ошибка при удалении: $_" -ForegroundColor Red
    Write-Host "  [INFO] Попробуйте удалить вручную через:" -ForegroundColor Yellow
    Write-Host "    Параметры → Приложения → Установленные приложения" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Удаление завершено!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

pause

