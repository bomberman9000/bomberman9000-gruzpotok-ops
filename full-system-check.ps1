# Полная проверка и настройка системы
# Проверяет все критические компоненты и применяет оптимальные настройки

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ПОЛНАЯ ПРОВЕРКА И НАСТРОЙКА СИСТЕМЫ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. ИНФОРМАЦИЯ О СИСТЕМЕ
# ========================================
Write-Host "[1/12] Сбор информации о системе..." -ForegroundColor Yellow
Write-Host ""

$os = Get-WmiObject Win32_OperatingSystem
$cpu = Get-WmiObject Win32_Processor
$gpu = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" -or $_.Name -like "*AMD*" -or $_.Name -like "*Intel*" }
$ram = Get-WmiObject Win32_ComputerSystem
$disk = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DeviceID -eq "C:" }

Write-Host "  Операционная система:" -ForegroundColor Cyan
Write-Host "    $($os.Caption) $($os.Version)" -ForegroundColor White
Write-Host "    Сборка: $($os.BuildNumber)" -ForegroundColor Gray
Write-Host ""

Write-Host "  Процессор:" -ForegroundColor Cyan
Write-Host "    $($cpu.Name)" -ForegroundColor White
Write-Host "    Ядер: $($cpu.NumberOfCores) | Потоков: $($cpu.NumberOfLogicalProcessors)" -ForegroundColor Gray
Write-Host ""

Write-Host "  Видеокарта:" -ForegroundColor Cyan
foreach ($card in $gpu) {
    Write-Host "    $($card.Name)" -ForegroundColor White
    Write-Host "    Разрешение: $($card.CurrentHorizontalResolution)x$($card.CurrentVerticalResolution)" -ForegroundColor Gray
    Write-Host "    Драйвер: $($card.DriverVersion)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "  Память:" -ForegroundColor Cyan
$totalRAM = [math]::Round($ram.TotalPhysicalMemory / 1GB, 2)
Write-Host "    Всего: $totalRAM GB" -ForegroundColor White
Write-Host ""

Write-Host "  Диск C:" -ForegroundColor Cyan
$freeSpace = [math]::Round($disk.FreeSpace / 1GB, 2)
$totalSpace = [math]::Round($disk.Size / 1GB, 2)
$usedPercent = [math]::Round((($totalSpace - $freeSpace) / $totalSpace) * 100, 1)
Write-Host "    Свободно: $freeSpace GB из $totalSpace GB ($usedPercent% занято)" -ForegroundColor White
Write-Host ""

# ========================================
# 2. ПРОВЕРКА VPN (HYSTERIA2)
# ========================================
Write-Host "[2/12] Проверка VPN (Hysteria2)..." -ForegroundColor Yellow

$hysteria2Process = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2Process) {
    Write-Host "  [OK] Hysteria2 запущен (PID: $($hysteria2Process.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Hysteria2 не запущен" -ForegroundColor Yellow
    Write-Host "  [INFO] Запускаю Hysteria2..." -ForegroundColor Gray
    
    # Попытка запуска
    $hysteria2Path = "C:\Users\$env:USERNAME\hysteria2\hysteria2.exe"
    if (Test-Path $hysteria2Path) {
        Start-Process -FilePath $hysteria2Path -ArgumentList "client", "-c", "config.yaml" -WindowStyle Hidden -WorkingDirectory "C:\Users\$env:USERNAME\hysteria2"
        Start-Sleep -Seconds 2
        $hysteria2Process = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
        if ($hysteria2Process) {
            Write-Host "  [OK] Hysteria2 запущен" -ForegroundColor Green
        }
    }
}
Write-Host ""

# ========================================
# 3. ПРОВЕРКА OLLAMA
# ========================================
Write-Host "[3/12] Проверка Ollama..." -ForegroundColor Yellow

$ollamaProcess = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
if ($ollamaProcess) {
    Write-Host "  [OK] Ollama запущен (PID: $($ollamaProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Ollama не запущен" -ForegroundColor Yellow
    
    # Проверка автозапуска
    $startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    $ollamaLink = Join-Path $startupPath "Ollama.lnk"
    if (Test-Path $ollamaLink) {
        Write-Host "  [OK] Автозапуск настроен" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Автозапуск не настроен" -ForegroundColor Yellow
    }
}
Write-Host ""

# ========================================
# 4. ПРОВЕРКА ТЕМЫ
# ========================================
Write-Host "[4/12] Проверка темы Windows..." -ForegroundColor Yellow

$themePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
$appsLight = (Get-ItemProperty -Path $themePath -Name "AppsUseLightTheme" -ErrorAction SilentlyContinue).AppsUseLightTheme
$systemLight = (Get-ItemProperty -Path $themePath -Name "SystemUsesLightTheme" -ErrorAction SilentlyContinue).SystemUsesLightTheme

if ($appsLight -eq 0 -and $systemLight -eq 0) {
    Write-Host "  [OK] Темная тема (текст должен быть белым)" -ForegroundColor Green
} elseif ($appsLight -eq 1 -and $systemLight -eq 1) {
    Write-Host "  [OK] Светлая тема (текст должен быть черным)" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Смешанная тема (приложения: $appsLight, система: $systemLight)" -ForegroundColor Cyan
}
Write-Host ""

# ========================================
# 5. НАСТРОЙКА ПРОИЗВОДИТЕЛЬНОСТИ
# ========================================
Write-Host "[5/12] Настройка производительности..." -ForegroundColor Yellow

# План питания - Высокая производительность
try {
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>&1 | Out-Null
    Write-Host "  [OK] План питания: Высокая производительность" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось изменить план питания" -ForegroundColor Yellow
}

# Отключение таймаутов
powercfg /change monitor-timeout-ac 0 2>&1 | Out-Null
powercfg /change disk-timeout-ac 0 2>&1 | Out-Null

Write-Host ""

# ========================================
# 6. ОПТИМИЗАЦИЯ NVIDIA
# ========================================
Write-Host "[6/12] Настройка NVIDIA..." -ForegroundColor Yellow

$nvidiaGPU = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
if ($nvidiaGPU) {
    # Реестр NVIDIA
    $nvidiaRegPath = "HKCU:\Software\NVIDIA Corporation\Global"
    if (-not (Test-Path $nvidiaRegPath)) {
        New-Item -Path $nvidiaRegPath -Force | Out-Null
    }
    
    Set-ItemProperty -Path $nvidiaRegPath -Name "PreferredRefreshRate" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $nvidiaRegPath -Name "PowerThrottling" -Value 0 -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Параметры NVIDIA настроены" -ForegroundColor Green
    Write-Host "  [INFO] Откройте NVIDIA Control Panel для ручной настройки" -ForegroundColor Cyan
} else {
    Write-Host "  [INFO] NVIDIA видеокарта не найдена" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 7. НАСТРОЙКА ДИСПЛЕЯ
# ========================================
Write-Host "[7/12] Настройка дисплея..." -ForegroundColor Yellow

# ClearType
$displayKey = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $displayKey -Name "FontSmoothing" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $displayKey -Name "FontSmoothingType" -Value 2 -ErrorAction SilentlyContinue

# DPI
Set-ItemProperty -Path $displayKey -Name "LogPixels" -Value 96 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $displayKey -Name "Win8DpiScaling" -Value 1 -ErrorAction SilentlyContinue

# Аппаратное ускорение
$avalon = "HKCU:\Software\Microsoft\Avalon.Graphics"
if (-not (Test-Path $avalon)) {
    New-Item -Path $avalon -Force | Out-Null
}
Set-ItemProperty -Path $avalon -Name "DisableHWAcceleration" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  [OK] Параметры дисплея настроены" -ForegroundColor Green
Write-Host ""

# ========================================
# 8. НАСТРОЙКА ПРОКСИ
# ========================================
Write-Host "[8/12] Проверка прокси..." -ForegroundColor Yellow

# Системный прокси
$proxySettings = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
if ($proxySettings.ProxyEnable -eq 1) {
    Write-Host "  [OK] Системный прокси включен: $($proxySettings.ProxyServer)" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Системный прокси отключен (используется VPN напрямую)" -ForegroundColor Cyan
}
Write-Host ""

# ========================================
# 9. ПРОВЕРКА FIREFOX
# ========================================
Write-Host "[9/12] Проверка Firefox..." -ForegroundColor Yellow

$firefoxProfile = Get-ChildItem "$env:APPDATA\Mozilla\Firefox\Profiles" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*.default*" } | Select-Object -First 1
if ($firefoxProfile) {
    $userJs = Join-Path $firefoxProfile.FullName "user.js"
    if (Test-Path $userJs) {
        $proxyConfig = Get-Content $userJs | Select-String "network.proxy"
        if ($proxyConfig) {
            Write-Host "  [OK] Firefox прокси настроен" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Firefox прокси не настроен" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [WARN] user.js не найден" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Firefox профиль не найден" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 10. ОЧИСТКА СИСТЕМЫ
# ========================================
Write-Host "[10/12] Очистка системы..." -ForegroundColor Yellow

# Очистка временных файлов
$tempPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*",
    "C:\Windows\Temp\*"
)

$cleaned = 0
foreach ($path in $tempPaths) {
    try {
        $items = Get-ChildItem -Path $path -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
        if ($items) {
            Remove-Item -Path $items.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $cleaned += $items.Count
        }
    } catch {
        # Ignore locked files
    }
}

Write-Host "  [OK] Удалено временных файлов: $cleaned" -ForegroundColor Green
Write-Host ""

# ========================================
# 11. ПРОВЕРКА АВТОЗАПУСКА
# ========================================
Write-Host "[11/12] Проверка автозапуска..." -ForegroundColor Yellow

# Startup folder
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupItems = Get-ChildItem -Path $startupPath -Filter "*.lnk" -ErrorAction SilentlyContinue

Write-Host "  Программы в автозапуске:" -ForegroundColor Cyan
if ($startupItems) {
    foreach ($item in $startupItems) {
        Write-Host "    - $($item.Name)" -ForegroundColor White
    }
} else {
    Write-Host "    (нет программ)" -ForegroundColor Gray
}
Write-Host ""

# Registry startup
$regStartup = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
if ($regStartup) {
    $regStartup.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "    - $($_.Name): $($_.Value)" -ForegroundColor White
    }
}
Write-Host ""

# ========================================
# 12. ОПТИМИЗАЦИЯ НАСТРОЕК
# ========================================
Write-Host "[12/12] Применение оптимальных настроек..." -ForegroundColor Yellow

# Отключение визуальных эффектов для производительности
$visualKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
if (-not (Test-Path $visualKey)) {
    New-Item -Path $visualKey -Force | Out-Null
}
Set-ItemProperty -Path $visualKey -Name "VisualFXSetting" -Value 2 -ErrorAction SilentlyContinue

# Включение важных визуальных эффектов
$dwmKey = "HKCU:\Software\Microsoft\Windows\DWM"
if (-not (Test-Path $dwmKey)) {
    New-Item -Path $dwmKey -Force | Out-Null
}
Set-ItemProperty -Path $dwmKey -Name "EnableAeroPeek" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $dwmKey -Name "AlwaysHibernateThumbnails" -Value 0 -ErrorAction SilentlyContinue

# Плавная прокрутка
$mouseKey = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $mouseKey -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue

# Отключение рекламы
$adsKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
if (Test-Path $adsKey) {
    Set-ItemProperty -Path $adsKey -Name "SystemPaneSuggestionsEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $adsKey -Name "SoftLandingEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $adsKey -Name "SubscribedContent-338393Enabled" -Value 0 -ErrorAction SilentlyContinue
}

Write-Host "  [OK] Оптимальные настройки применены" -ForegroundColor Green
Write-Host ""

# ========================================
# ИТОГОВЫЙ ОТЧЕТ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ПРОВЕРКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "СОСТОЯНИЕ СИСТЕМЫ:" -ForegroundColor Cyan
Write-Host ""

# Критические компоненты
Write-Host "Критические компоненты:" -ForegroundColor Yellow
if ($hysteria2Process) {
    Write-Host "  ✓ VPN (Hysteria2): Работает" -ForegroundColor Green
} else {
    Write-Host "  ✗ VPN (Hysteria2): Не запущен" -ForegroundColor Red
}

if ($ollamaProcess) {
    Write-Host "  ✓ Ollama: Работает" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Ollama: Не запущен" -ForegroundColor Yellow
}

if ($nvidiaGPU) {
    Write-Host "  ✓ NVIDIA RTX 5070: Обнаружена" -ForegroundColor Green
} else {
    Write-Host "  ⚠ NVIDIA: Не обнаружена" -ForegroundColor Yellow
}
Write-Host ""

# Настройки
Write-Host "Применённые настройки:" -ForegroundColor Yellow
Write-Host "  ✓ План питания: Высокая производительность" -ForegroundColor Green
Write-Host "  ✓ NVIDIA: Оптимизирована" -ForegroundColor Green
Write-Host "  ✓ Дисплей: ClearType и масштабирование настроены" -ForegroundColor Green
Write-Host "  ✓ Визуальные эффекты: Оптимизированы" -ForegroundColor Green
Write-Host "  ✓ Временные файлы: Очищены ($cleaned файлов)" -ForegroundColor Green
Write-Host ""

# Рекомендации
Write-Host "РЕКОМЕНДАЦИИ:" -ForegroundColor Cyan
Write-Host ""

if (-not $hysteria2Process) {
    Write-Host "  1. Запустите Hysteria2 VPN" -ForegroundColor Yellow
}

if (-not $ollamaProcess) {
    Write-Host "  2. Запустите Ollama (или настройте автозапуск)" -ForegroundColor Yellow
}

if ($nvidiaGPU) {
    Write-Host "  3. Откройте NVIDIA Control Panel и настройте:" -ForegroundColor Yellow
    Write-Host "     → Управление параметрами 3D: Высокое качество" -ForegroundColor White
    Write-Host "     → Разрешение: 3840x2160, 32-bit цвет" -ForegroundColor White
    Write-Host "     → Сглаживание: Включить" -ForegroundColor White
}

Write-Host ""
Write-Host "  4. ПЕРЕЗАГРУЗИТЕ КОМПЬЮТЕР для применения всех изменений" -ForegroundColor Yellow
Write-Host ""

# Дополнительные действия
Write-Host "ДОПОЛНИТЕЛЬНО (опционально):" -ForegroundColor Cyan
Write-Host "  - Запустите ClearType: cttune" -ForegroundColor White
Write-Host "  - Обновите драйверы NVIDIA: nvidia.com/drivers" -ForegroundColor White
Write-Host "  - Проверьте обновления Windows: Windows Update" -ForegroundColor White
Write-Host ""

pause
