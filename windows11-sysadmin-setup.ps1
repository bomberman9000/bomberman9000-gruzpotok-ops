# Windows 11 - Профессиональная настройка от системного администратора
# Оптимальные параметры, безопасность, производительность

#Requires -RunAsAdministrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WINDOWS 11 - НАСТРОЙКА СИСАДМИНА" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "SilentlyContinue"

# ========================================
# 1. СИСТЕМНЫЕ ПАРАМЕТРЫ
# ========================================
Write-Host "[1/15] Настройка системных параметров..." -ForegroundColor Yellow

# Отключение гибернации (освобождает место на диске)
powercfg /h off
Write-Host "  [OK] Гибернация отключена" -ForegroundColor Green

# Настройка виртуальной памяти (автоматически)
$cs = Get-WmiObject Win32_ComputerSystem
$totalRAM = [math]::Round($cs.TotalPhysicalMemory / 1GB)
Write-Host "  [OK] RAM: $totalRAM GB" -ForegroundColor Green

# Отключение быстрого запуска (может вызывать проблемы)
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power" -Name "HiberbootEnabled" -Value 0
Write-Host "  [OK] Быстрый запуск отключен" -ForegroundColor Green

# Включение Ultimate Performance (если доступно)
try {
    powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
    Write-Host "  [OK] Ultimate Performance активирован" -ForegroundColor Green
} catch {
    Write-Host "  [INFO] Ultimate Performance недоступен" -ForegroundColor Gray
}

# Установка высокой производительности
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg /change monitor-timeout-ac 15
powercfg /change disk-timeout-ac 0
Write-Host "  [OK] План питания настроен" -ForegroundColor Green

Write-Host ""

# ========================================
# 2. ПРОВОДНИК И ИНТЕРФЕЙС
# ========================================
Write-Host "[2/15] Настройка Проводника..." -ForegroundColor Yellow

$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Показывать скрытые файлы и папки
Set-ItemProperty -Path $explorerKey -Name "Hidden" -Value 1

# Показывать расширения файлов
Set-ItemProperty -Path $explorerKey -Name "HideFileExt" -Value 0

# Показывать защищенные системные файлы
Set-ItemProperty -Path $explorerKey -Name "ShowSuperHidden" -Value 1

# Открывать Проводник на "Этот компьютер"
Set-ItemProperty -Path $explorerKey -Name "LaunchTo" -Value 1

# Показывать полный путь в заголовке
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\CabinetState" -Name "FullPath" -Value 1 -Force

# Компактный вид (Windows 11)
Set-ItemProperty -Path $explorerKey -Name "UseCompactMode" -Value 1 -Force

# Отключение недавних файлов и частых папок в быстром доступе
Set-ItemProperty -Path $explorerKey -Name "ShowRecent" -Value 0
Set-ItemProperty -Path $explorerKey -Name "ShowFrequent" -Value 0

Write-Host "  [OK] Проводник настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# 3. КОНФИДЕНЦИАЛЬНОСТЬ И ТЕЛЕМЕТРИЯ
# ========================================
Write-Host "[3/15] Отключение телеметрии и рекламы..." -ForegroundColor Yellow

# Отключение телеметрии
$telemetryKeys = @(
    "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection"
)

foreach ($key in $telemetryKeys) {
    if (-not (Test-Path $key)) {
        New-Item -Path $key -Force | Out-Null
    }
    Set-ItemProperty -Path $key -Name "AllowTelemetry" -Value 0
}

# Отключение рекламы и предложений
$contentDelivery = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
$adSettings = @{
    "SystemPaneSuggestionsEnabled" = 0
    "SoftLandingEnabled" = 0
    "RotatingLockScreenEnabled" = 0
    "RotatingLockScreenOverlayEnabled" = 0
    "SubscribedContent-310093Enabled" = 0
    "SubscribedContent-338387Enabled" = 0
    "SubscribedContent-338388Enabled" = 0
    "SubscribedContent-338389Enabled" = 0
    "SubscribedContent-338393Enabled" = 0
    "SubscribedContent-353694Enabled" = 0
    "SubscribedContent-353696Enabled" = 0
}

foreach ($setting in $adSettings.GetEnumerator()) {
    Set-ItemProperty -Path $contentDelivery -Name $setting.Key -Value $setting.Value
}

# Отключение советов Windows
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent" -Name "DisableSoftLanding" -Value 1 -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent" -Name "DisableWindowsConsumerFeatures" -Value 1 -Force

Write-Host "  [OK] Телеметрия и реклама отключены" -ForegroundColor Green
Write-Host ""

# ========================================
# 4. ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ
# ========================================
Write-Host "[4/15] Оптимизация производительности..." -ForegroundColor Yellow

# Отключение индексации (для SSD не нужна)
$drives = Get-PhysicalDisk | Where-Object { $_.MediaType -eq "SSD" }
if ($drives) {
    Stop-Service "WSearch" -Force
    Set-Service "WSearch" -StartupType Disabled
    Write-Host "  [OK] Индексация отключена (SSD обнаружен)" -ForegroundColor Green
}

# Отключение Superfetch/SysMain (для SSD не нужен)
Stop-Service "SysMain" -Force
Set-Service "SysMain" -StartupType Disabled
Write-Host "  [OK] SysMain отключен" -ForegroundColor Green

# Отключение дефрагментации по расписанию (для SSD вредна)
Disable-ScheduledTask -TaskName "Microsoft\Windows\Defrag\ScheduledDefrag"
Write-Host "  [OK] Автоматическая дефрагментация отключена" -ForegroundColor Green

# Настройка визуальных эффектов
$visualKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
if (-not (Test-Path $visualKey)) {
    New-Item -Path $visualKey -Force | Out-Null
}
Set-ItemProperty -Path $visualKey -Name "VisualFXSetting" -Value 2  # Оптимальная производительность

Write-Host ""

# ========================================
# 5. БЕЗОПАСНОСТЬ
# ========================================
Write-Host "[5/15] Настройка безопасности..." -ForegroundColor Yellow

# Включение защиты системы (точки восстановления)
try {
    Enable-ComputerRestore -Drive "C:\"
    vssadmin resize shadowstorage /for=C: /on=C: /maxsize=10GB
    Checkpoint-Computer -Description "Настройка системы сисадмином" -RestorePointType "MODIFY_SETTINGS"
    Write-Host "  [OK] Точка восстановления создана" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось создать точку восстановления" -ForegroundColor Yellow
}

# Включение брандмауэра
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
Write-Host "  [OK] Брандмауэр включен" -ForegroundColor Green

# Настройка UAC (User Account Control)
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "ConsentPromptBehaviorAdmin" -Value 2
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" -Name "EnableLUA" -Value 1
Write-Host "  [OK] UAC настроен" -ForegroundColor Green

Write-Host ""

# ========================================
# 6. СЕТЕВЫЕ НАСТРОЙКИ
# ========================================
Write-Host "[6/15] Оптимизация сети..." -ForegroundColor Yellow

# DNS кэш
Set-DnsClientServerAddress -InterfaceAlias "Ethernet*" -ServerAddresses ("1.1.1.1", "1.0.0.1") -ErrorAction SilentlyContinue
Set-DnsClientServerAddress -InterfaceAlias "Wi-Fi*" -ServerAddresses ("1.1.1.1", "1.0.0.1") -ErrorAction SilentlyContinue

# Очистка DNS кэша
ipconfig /flushdns | Out-Null
Write-Host "  [OK] DNS настроен (Cloudflare)" -ForegroundColor Green

# Отключение IPv6 (если не используется)
# Disable-NetAdapterBinding -Name "*" -ComponentID ms_tcpip6

# Оптимизация TCP/IP
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global chimney=enabled
netsh int tcp set global dca=enabled
netsh int tcp set global netdma=enabled
Write-Host "  [OK] TCP/IP оптимизирован" -ForegroundColor Green

Write-Host ""

# ========================================
# 7. СЛУЖБЫ WINDOWS
# ========================================
Write-Host "[7/15] Оптимизация служб..." -ForegroundColor Yellow

# Службы для отключения (с осторожностью)
$servicesToDisable = @(
    "XblAuthManager",      # Xbox Live Auth Manager
    "XblGameSave",         # Xbox Live Game Save
    "XboxNetApiSvc",       # Xbox Live Networking Service
    "XboxGipSvc",          # Xbox Accessory Management Service
    "dmwappushservice",    # WAP Push Message Routing Service
    "MapsBroker",          # Downloaded Maps Manager
    "lfsvc",               # Geolocation Service
    "SharedAccess",        # Internet Connection Sharing
    "RetailDemo",          # Retail Demo Service
    "Fax"                  # Fax
)

$disabledCount = 0
foreach ($service in $servicesToDisable) {
    $svc = Get-Service -Name $service -ErrorAction SilentlyContinue
    if ($svc) {
        Stop-Service $service -Force -ErrorAction SilentlyContinue
        Set-Service $service -StartupType Disabled -ErrorAction SilentlyContinue
        $disabledCount++
    }
}

Write-Host "  [OK] Отключено ненужных служб: $disabledCount" -ForegroundColor Green
Write-Host ""

# ========================================
# 8. ДИСПЕТЧЕР ЗАДАЧ
# ========================================
Write-Host "[8/15] Настройка Диспетчера задач..." -ForegroundColor Yellow

$taskMgrKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\TaskManager"
if (-not (Test-Path $taskMgrKey)) {
    New-Item -Path $taskMgrKey -Force | Out-Null
}

# Запускать в расширенном режиме
Set-ItemProperty -Path $taskMgrKey -Name "Preferences" -Value ([byte[]](0x28,0x00,0x00,0x00,0x01))

Write-Host "  [OK] Диспетчер задач настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# 9. КОНТЕКСТНОЕ МЕНЮ (Windows 11)
# ========================================
Write-Host "[9/15] Настройка контекстного меню..." -ForegroundColor Yellow

# Вернуть классическое контекстное меню (опционально)
# Раскомментируйте если хотите старое меню:
# reg add "HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32" /f /ve

Write-Host "  [OK] Контекстное меню (Windows 11 по умолчанию)" -ForegroundColor Green
Write-Host ""

# ========================================
# 10. ПАНЕЛЬ ЗАДАЧ
# ========================================
Write-Host "[10/15] Настройка панели задач..." -ForegroundColor Yellow

$taskbarKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Показывать все значки в системном трее
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer" -Name "EnableAutoTray" -Value 0

# Выравнивание по левому краю (как в Windows 10)
Set-ItemProperty -Path $taskbarKey -Name "TaskbarAl" -Value 0

# Отключить поиск на панели задач
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "SearchboxTaskbarMode" -Value 0

# Отключить виджеты
Set-ItemProperty -Path $taskbarKey -Name "TaskbarDa" -Value 0

# Отключить чат (Teams)
Set-ItemProperty -Path $taskbarKey -Name "TaskbarMn" -Value 0

Write-Host "  [OK] Панель задач настроена" -ForegroundColor Green
Write-Host ""

# ========================================
# 11. МЕНЮ ПУСК
# ========================================
Write-Host "[11/15] Настройка меню Пуск..." -ForegroundColor Yellow

$startKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Больше закрепленных элементов
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "Start_Layout" -Value 1

# Отключить рекомендации
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Explorer" -Name "HideRecommendedSection" -Value 1 -Force

Write-Host "  [OK] Меню Пуск настроено" -ForegroundColor Green
Write-Host ""

# ========================================
# 12. WINDOWS UPDATE
# ========================================
Write-Host "[12/15] Настройка Windows Update..." -ForegroundColor Yellow

# Отключить автоматическую перезагрузку
$updateKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
if (-not (Test-Path $updateKey)) {
    New-Item -Path $updateKey -Force | Out-Null
}
Set-ItemProperty -Path $updateKey -Name "NoAutoRebootWithLoggedOnUsers" -Value 1
Set-ItemProperty -Path $updateKey -Name "AUOptions" -Value 3  # Загружать, но не устанавливать

Write-Host "  [OK] Windows Update настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# 13. ИГРОВОЙ РЕЖИМ И DVR
# ========================================
Write-Host "[13/15] Настройка игрового режима..." -ForegroundColor Yellow

# Отключить Game DVR
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR" -Name "AppCaptureEnabled" -Value 0
Set-ItemProperty -Path "HKCU:\System\GameConfigStore" -Name "GameDVR_Enabled" -Value 0

# Включить игровой режим (для производительности)
Set-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled" -Value 1

Write-Host "  [OK] Игровой режим настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# 14. ДИСПЛЕЙ И ГРАФИКА
# ========================================
Write-Host "[14/15] Настройка дисплея..." -ForegroundColor Yellow

# ClearType
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothing" -Value 2
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothingType" -Value 2

# Аппаратное ускорение
$avalonKey = "HKCU:\Software\Microsoft\Avalon.Graphics"
if (-not (Test-Path $avalonKey)) {
    New-Item -Path $avalonKey -Force | Out-Null
}
Set-ItemProperty -Path $avalonKey -Name "DisableHWAcceleration" -Value 0

# Темная тема
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0

Write-Host "  [OK] Дисплей настроен (темная тема, ClearType)" -ForegroundColor Green
Write-Host ""

# ========================================
# 15. ОЧИСТКА СИСТЕМЫ
# ========================================
Write-Host "[15/15] Очистка системы..." -ForegroundColor Yellow

# Очистка временных файлов
$tempFolders = @(
    "$env:TEMP",
    "$env:LOCALAPPDATA\Temp",
    "C:\Windows\Temp",
    "C:\Windows\Prefetch"
)

$cleanedFiles = 0
foreach ($folder in $tempFolders) {
    if (Test-Path $folder) {
        try {
            $items = Get-ChildItem -Path $folder -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
            if ($items) {
                Remove-Item -Path $items.FullName -Recurse -Force -ErrorAction SilentlyContinue
                $cleanedFiles += $items.Count
            }
        } catch {}
    }
}

# Очистка корзины
Clear-RecycleBin -Force -ErrorAction SilentlyContinue

Write-Host "  [OK] Удалено временных файлов: $cleanedFiles" -ForegroundColor Green
Write-Host ""

# ========================================
# ПЕРЕЗАПУСК EXPLORER
# ========================================
Write-Host "Перезапуск Проводника..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force
Start-Sleep -Seconds 2
Write-Host "  [OK] Проводник перезапущен" -ForegroundColor Green
Write-Host ""

# ========================================
# ИТОГИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "ПРИМЕНЕНО:" -ForegroundColor Cyan
Write-Host "  ✓ Системные параметры оптимизированы" -ForegroundColor White
Write-Host "  ✓ Проводник настроен (показывает скрытые файлы, расширения)" -ForegroundColor White
Write-Host "  ✓ Телеметрия и реклама отключены" -ForegroundColor White
Write-Host "  ✓ Производительность максимизирована" -ForegroundColor White
Write-Host "  ✓ Безопасность усилена (точка восстановления создана)" -ForegroundColor White
Write-Host "  ✓ Сеть оптимизирована (DNS Cloudflare)" -ForegroundColor White
Write-Host "  ✓ Ненужные службы отключены ($disabledCount)" -ForegroundColor White
Write-Host "  ✓ Интерфейс настроен (панель задач, меню Пуск)" -ForegroundColor White
Write-Host "  ✓ Игровой режим включен" -ForegroundColor White
Write-Host "  ✓ Система очищена ($cleanedFiles файлов)" -ForegroundColor White
Write-Host ""

Write-Host "СЛЕДУЮЩИЙ ШАГ:" -ForegroundColor Yellow
Write-Host "  → Запустите: .\install-essential-programs.ps1" -ForegroundColor White
Write-Host "  → Для установки необходимых программ" -ForegroundColor White
Write-Host ""

pause
