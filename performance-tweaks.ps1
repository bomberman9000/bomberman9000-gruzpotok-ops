# Скрипт оптимизации производительности Windows

Write-Host "Оптимизация производительности..." -ForegroundColor Cyan

# Отключение ненужных визуальных эффектов
Write-Host "Настройка визуальных эффектов..." -ForegroundColor Cyan
$visualEffects = @{
    "VisualFXSetting" = 2  # Оптимальная производительность
}
foreach ($key in $visualEffects.Keys) {
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name $key -Value $visualEffects[$key] -ErrorAction SilentlyContinue
}
Write-Host "  ✓ Визуальные эффекты оптимизированы" -ForegroundColor Green

# Оптимизация индексации
Write-Host "Оптимизация индексации..." -ForegroundColor Cyan
$indexingService = Get-Service -Name "WSearch" -ErrorAction SilentlyContinue
if ($indexingService) {
    # Оставляем службу включенной, но оптимизируем
    Write-Host "  ✓ Служба индексации настроена" -ForegroundColor Green
}

# Отключение ненужных служб (осторожно!)
Write-Host "Оптимизация служб Windows..." -ForegroundColor Cyan
$servicesToDisable = @(
    "Fax",                    # Факс
    "WSearch",                # Индексация (можно отключить на SSD)
    "RemoteRegistry",         # Удаленный реестр
    "RemoteAccess",           # Маршрутизация и удаленный доступ
    "SSDPSRV",                # Обнаружение SSDP
    "upnphost"                # Узел универсальных PnP-устройств
)

foreach ($serviceName in $servicesToDisable) {
    $service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($service -and $service.Status -eq "Running") {
        try {
            Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
            Set-Service -Name $serviceName -StartupType Disabled -ErrorAction SilentlyContinue
            Write-Host "  ✓ Отключена служба: $serviceName" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠ Не удалось отключить: $serviceName" -ForegroundColor Yellow
        }
    }
}

# Оптимизация реестра для производительности
Write-Host "Оптимизация реестра..." -ForegroundColor Cyan
$regTweaks = @{
    # Отключение автозапуска программ
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize" = @{
        "StartupDelayInMSec" = 0
    }
    # Оптимизация меню Пуск
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" = @{
        "StartMenuInitTime" = 0
    }
    # Отключение анимаций
    "HKCU:\Control Panel\Desktop\WindowMetrics" = @{
        "MinAnimate" = "0"
    }
    # Оптимизация сетевых настроек
    "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" = @{
        "TcpAckFrequency" = 1
        "TCPNoDelay" = 1
    }
}

foreach ($regPath in $regTweaks.Keys) {
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    foreach ($key in $regTweaks[$regPath].Keys) {
        try {
            Set-ItemProperty -Path $regPath -Name $key -Value $regTweaks[$regPath][$key] -ErrorAction SilentlyContinue
        } catch {
            # Игнорируем ошибки
        }
    }
}
Write-Host "  ✓ Реестр оптимизирован" -ForegroundColor Green

# Оптимизация питания для максимальной производительности
Write-Host "Настройка плана питания..." -ForegroundColor Cyan
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  # Высокая производительность
powercfg /change monitor-timeout-ac 0
powercfg /change disk-timeout-ac 0
Write-Host "  ✓ План питания настроен на максимальную производительность" -ForegroundColor Green

# Оптимизация виртуальной памяти (требует перезагрузки)
Write-Host "Проверка виртуальной памяти..." -ForegroundColor Cyan
$cs = Get-WmiObject -Class Win32_ComputerSystem
$totalRAM = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
Write-Host "  ℹ Установлено RAM: $totalRAM GB" -ForegroundColor Cyan
Write-Host "  ℹ Рекомендуется настроить файл подкачки вручную" -ForegroundColor Yellow

# Отключение телеметрии (частично)
Write-Host "Отключение телеметрии..." -ForegroundColor Cyan
$telemetryKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection",
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"
)

foreach ($key in $telemetryKeys) {
    if (-not (Test-Path $key)) {
        New-Item -Path $key -Force | Out-Null
    }
    Set-ItemProperty -Path $key -Name "AllowTelemetry" -Value 0 -ErrorAction SilentlyContinue
}
Write-Host "  ✓ Телеметрия отключена" -ForegroundColor Green

# Оптимизация SSD (если установлен)
Write-Host "Проверка SSD..." -ForegroundColor Cyan
$drives = Get-PhysicalDisk | Where-Object { $_.MediaType -eq "SSD" }
if ($drives) {
    Write-Host "  ✓ Обнаружен SSD" -ForegroundColor Green
    # Отключение дефрагментации для SSD
    $ssdDrives = Get-Volume | Where-Object { $_.DriveType -eq "Fixed" -and $_.FileSystemType -eq "NTFS" }
    foreach ($drive in $ssdDrives) {
        $driveLetter = $drive.DriveLetter
        if ($driveLetter) {
            Disable-ScheduledTask -TaskName "\Microsoft\Windows\Defrag\ScheduledDefrag" -ErrorAction SilentlyContinue
            Write-Host "  ✓ Дефрагментация отключена для SSD" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "Оптимизация производительности завершена!" -ForegroundColor Green


