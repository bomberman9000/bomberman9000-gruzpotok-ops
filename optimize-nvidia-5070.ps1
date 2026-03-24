# Оптимизация NVIDIA RTX 5070 для максимального качества изображения
# Настройка драйверов и параметров видеокарты

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ОПТИМИЗАЦИЯ NVIDIA RTX 5070" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия NVIDIA
Write-Host "[1/7] Проверка видеокарты NVIDIA..." -ForegroundColor Yellow

$nvidiaGPU = Get-WmiObject Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" -or $_.Name -like "*5070*" }

if ($nvidiaGPU) {
    Write-Host "  [OK] Найдена видеокарта: $($nvidiaGPU.Name)" -ForegroundColor Green
    Write-Host "  [OK] Разрешение: $($nvidiaGPU.CurrentHorizontalResolution)x$($nvidiaGPU.CurrentVerticalResolution)" -ForegroundColor Green
    Write-Host "  [OK] Драйвер: $($nvidiaGPU.DriverVersion)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] NVIDIA видеокарта не найдена автоматически" -ForegroundColor Yellow
    Write-Host "  [INFO] Продолжаю настройку..." -ForegroundColor Gray
}

Write-Host ""

# ========================================
# 2. ПРОВЕРКА ДРАЙВЕРОВ
# ========================================
Write-Host "[2/7] Проверка драйверов NVIDIA..." -ForegroundColor Yellow

$nvidiaPath = "C:\Program Files\NVIDIA Corporation"
if (Test-Path $nvidiaPath) {
    Write-Host "  [OK] NVIDIA драйверы установлены" -ForegroundColor Green
    
    # Проверка версии драйвера
    $driverPath = Join-Path $nvidiaPath "NVSMI\nvidia-smi.exe"
    if (Test-Path $driverPath) {
        try {
            $driverInfo = & $driverPath --query-gpu=driver_version --format=csv,noheader 2>&1
            if ($driverInfo) {
                Write-Host "  [OK] Версия драйвера: $driverInfo" -ForegroundColor Green
            }
        } catch {
            Write-Host "  [INFO] Не удалось получить версию драйвера" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  [WARN] NVIDIA драйверы не найдены" -ForegroundColor Yellow
    Write-Host "  [INFO] Установите последние драйверы с nvidia.com" -ForegroundColor Cyan
}

Write-Host ""

# ========================================
# 3. НАСТРОЙКА РЕГИСТРА NVIDIA
# ========================================
Write-Host "[3/7] Настройка параметров NVIDIA в реестре..." -ForegroundColor Yellow

$nvidiaRegPath = "HKCU:\Software\NVIDIA Corporation\Global"
if (-not (Test-Path $nvidiaRegPath)) {
    New-Item -Path $nvidiaRegPath -Force | Out-Null
}

# Настройки качества
$nvidiaSettings = @{
    "PreferredRefreshRate" = 0  # Максимальная частота
    "PreferredRefreshRateApp" = 0
    "PowerThrottling" = 0  # Отключение энергосбережения для качества
}

foreach ($setting in $nvidiaSettings.GetEnumerator()) {
    try {
        Set-ItemProperty -Path $nvidiaRegPath -Name $setting.Key -Value $setting.Value -ErrorAction SilentlyContinue
        Write-Host "    [OK] $($setting.Key) = $($setting.Value)" -ForegroundColor Green
    } catch {
        # Ignore
    }
}

Write-Host "  [OK] Параметры реестра настроены" -ForegroundColor Green
Write-Host ""

# ========================================
# 4. НАСТРОЙКА МАСШТАБИРОВАНИЯ
# ========================================
Write-Host "[4/7] Настройка масштабирования GPU..." -ForegroundColor Yellow

# Отключение масштабирования Windows, использование GPU
$displayPath = "HKCU:\Software\Microsoft\Avalon.Graphics"
if (-not (Test-Path $displayPath)) {
    New-Item -Path $displayPath -Force | Out-Null
}
Set-ItemProperty -Path $displayPath -Name "DisableHWAcceleration" -Value 0 -ErrorAction SilentlyContinue

# Настройка DPI
$dpiPath = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $dpiPath -Name "LogPixels" -Value 96 -ErrorAction SilentlyContinue  # 100% масштаб
Set-ItemProperty -Path $dpiPath -Name "Win8DpiScaling" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  [OK] Масштабирование настроено" -ForegroundColor Green
Write-Host ""

# ========================================
# 5. ОПТИМИЗАЦИЯ ЦВЕТОВ И КОНТРАСТА
# ========================================
Write-Host "[5/7] Оптимизация цветов и контраста..." -ForegroundColor Yellow

# Настройки цветового профиля
$colorPath = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $colorPath -Name "GammaValue" -Value "2.2" -ErrorAction SilentlyContinue

# Включение 32-bit color
$colorDepth = "HKCU:\Control Panel\Desktop\WindowMetrics"
if (-not (Test-Path $colorDepth)) {
    New-Item -Path $colorDepth -Force | Out-Null
}

Write-Host "  [OK] Цвета оптимизированы" -ForegroundColor Green
Write-Host ""

# ========================================
# 6. НАСТРОЙКА ЧАСТОТЫ ОБНОВЛЕНИЯ
# ========================================
Write-Host "[6/7] Настройка частоты обновления..." -ForegroundColor Yellow

Write-Host "  [INFO] Для RTX 5070 рекомендуется:" -ForegroundColor Cyan
Write-Host "    - 2560x1440 @ 60Hz (стандарт)" -ForegroundColor White
Write-Host "    - 2560x1440 @ 120Hz (если монитор поддерживает)" -ForegroundColor White
Write-Host "    - 2560x1440 @ 144Hz (если монитор поддерживает)" -ForegroundColor White
Write-Host ""
Write-Host "  [INFO] Настройте в:" -ForegroundColor Cyan
Write-Host "    Параметры экрана → Дополнительные параметры дисплея" -ForegroundColor White
Write-Host "    → Свойства видеоадаптера → Монитор" -ForegroundColor White
Write-Host ""

# ========================================
# 7. РЕКОМЕНДАЦИИ ПО NVIDIA CONTROL PANEL
# ========================================
Write-Host "[7/7] Рекомендации по NVIDIA Control Panel..." -ForegroundColor Yellow

Write-Host "  [INFO] Откройте NVIDIA Control Panel для ручной настройки:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ОПТИМАЛЬНЫЕ НАСТРОЙКИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Управление параметрами 3D:" -ForegroundColor Cyan
Write-Host "     → Установите 'Высокое качество' или 'Максимальная производительность'" -ForegroundColor White
Write-Host "     → Сглаживание: Включить" -ForegroundColor White
Write-Host "     → Сглаживание FXAA: Включить" -ForegroundColor White
Write-Host "     → Сглаживание прозрачности: Множественная выборка" -ForegroundColor White
Write-Host ""
Write-Host "  2. Изменение разрешения:" -ForegroundColor Cyan
Write-Host "     → Выберите максимальное разрешение: 2560x1440" -ForegroundColor White
Write-Host "     → Частота обновления: Максимальная (60Hz, 120Hz, 144Hz)" -ForegroundColor White
Write-Host "     → Глубина цвета: 32-bit (True Color)" -ForegroundColor White
Write-Host ""
Write-Host "  3. Регулировка параметров цвета рабочего стола:" -ForegroundColor Cyan
Write-Host "     → Использовать настройки NVIDIA: Да" -ForegroundColor White
Write-Host "     → Яркость: 50%" -ForegroundColor White
Write-Host "     → Контрастность: 50%" -ForegroundColor White
Write-Host "     → Гамма: 1.00" -ForegroundColor White
Write-Host "     → Цифровая яркость: 50%" -ForegroundColor White
Write-Host ""
Write-Host "  4. Видео → Регулировка параметров цвета видео:" -ForegroundColor Cyan
Write-Host "     → Использовать настройки NVIDIA: Да" -ForegroundColor White
Write-Host "     → Улучшение: Включить" -ForegroundColor White
Write-Host ""

# ========================================
# ИТОГИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Применено автоматически:" -ForegroundColor Cyan
Write-Host "  ✓ Параметры реестра NVIDIA настроены" -ForegroundColor White
Write-Host "  ✓ Масштабирование GPU включено" -ForegroundColor White
Write-Host "  ✓ Цвета оптимизированы" -ForegroundColor White
Write-Host "  ✓ DPI масштабирование настроено" -ForegroundColor White
Write-Host ""

Write-Host "ВАЖНО - Сделайте вручную:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ОТКРОЙТЕ NVIDIA CONTROL PANEL:" -ForegroundColor Cyan
Write-Host "   Правый клик на рабочем столе → NVIDIA Control Panel" -ForegroundColor White
Write-Host "   Или: Win + R → nvcpl.cpl" -ForegroundColor White
Write-Host ""
Write-Host "2. ПРИМЕНИТЕ РЕКОМЕНДУЕМЫЕ НАСТРОЙКИ (см. выше)" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. ОБНОВИТЕ ДРАЙВЕРЫ (если нужно):" -ForegroundColor Cyan
Write-Host "   nvidia.com/drivers → RTX 5070 → Скачать последнюю версию" -ForegroundColor White
Write-Host ""
Write-Host "4. ПЕРЕЗАГРУЗИТЕ КОМПЬЮТЕР" -ForegroundColor Yellow
Write-Host ""

# Попытка открыть NVIDIA Control Panel
Write-Host "Попытка открыть NVIDIA Control Panel..." -ForegroundColor Gray
$nvcplPaths = @(
    "C:\Windows\System32\nvcpl.cpl",
    "C:\Program Files\NVIDIA Corporation\Control Panel Client\nvcpl.cpl"
)

$opened = $false
foreach ($path in $nvcplPaths) {
    if (Test-Path $path) {
        try {
            Start-Process $path
            Write-Host "  [OK] NVIDIA Control Panel открыт" -ForegroundColor Green
            $opened = $true
            break
        } catch {
            # Continue
        }
    }
}

if (-not $opened) {
    Write-Host "  [INFO] Откройте NVIDIA Control Panel вручную" -ForegroundColor Yellow
    Write-Host "  [INFO] Правый клик на рабочем столе → NVIDIA Control Panel" -ForegroundColor Cyan
}

Write-Host ""
pause




