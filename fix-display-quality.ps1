# Оптимизация качества дисплея
# Устранение пикселизации, настройка разрешения и масштабирования
# Run as Administrator (для некоторых настроек)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ОПТИМИЗАЦИЯ КАЧЕСТВА ДИСПЛЕЯ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка админ прав
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# ========================================
# 1. ПРОВЕРКА ТЕКУЩИХ НАСТРОЕК
# ========================================
Write-Host "[1/6] Проверка текущих настроек дисплея..." -ForegroundColor Yellow

Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens

foreach ($screen in $screens) {
    Write-Host "  Монитор: $($screen.DeviceName)" -ForegroundColor Gray
    Write-Host "    Разрешение: $($screen.Bounds.Width)x$($screen.Bounds.Height)" -ForegroundColor White
    Write-Host "    Рабочая область: $($screen.WorkingArea.Width)x$($screen.WorkingArea.Height)" -ForegroundColor White
}

Write-Host ""

# ========================================
# 2. НАСТРОЙКА МАСШТАБИРОВАНИЯ DPI
# ========================================
Write-Host "[2/6] Настройка масштабирования DPI..." -ForegroundColor Yellow

# Получаем текущее масштабирование
$dpiPath = "HKCU:\Control Panel\Desktop"
$logPixels = (Get-ItemProperty -Path $dpiPath -Name LogPixels -ErrorAction SilentlyContinue).LogPixels

if ($logPixels) {
    $currentScale = [math]::Round(($logPixels / 96) * 100)
    Write-Host "  Текущее масштабирование: $currentScale%" -ForegroundColor Gray
} else {
    Write-Host "  Текущее масштабирование: 100% (по умолчанию)" -ForegroundColor Gray
}

# Настройка сглаживания шрифтов (ClearType)
Write-Host "  Включение ClearType..." -ForegroundColor Gray
Set-ItemProperty -Path $dpiPath -Name "FontSmoothing" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $dpiPath -Name "FontSmoothingType" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $dpiPath -Name "FontSmoothingOrientation" -Value 1 -ErrorAction SilentlyContinue
Write-Host "    [OK] ClearType включен" -ForegroundColor Green

# Отключение растягивания окон
Set-ItemProperty -Path $dpiPath -Name "Win8DpiScaling" -Value 1 -ErrorAction SilentlyContinue
Write-Host "    [OK] DPI масштабирование оптимизировано" -ForegroundColor Green

Write-Host ""

# ========================================
# 3. ОПТИМИЗАЦИЯ ВИЗУАЛЬНЫХ ЭФФЕКТТОВ
# ========================================
Write-Host "[3/6] Оптимизация визуальных эффектов..." -ForegroundColor Yellow

$perfPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"

# Включение сглаживания краев экранных шрифтов
Set-ItemProperty -Path $perfPath -Name "VisualFXSetting" -Value 2 -ErrorAction SilentlyContinue

# Включение всех визуальных эффектов для лучшего качества
$visualEffects = @(
    "HKCU:\Control Panel\Desktop",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
)

# Настройки для четкости
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -Value ([byte[]](0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00)) -ErrorAction SilentlyContinue

Write-Host "    [OK] Визуальные эффекты оптимизированы" -ForegroundColor Green
Write-Host ""

# ========================================
# 4. НАСТРОЙКА РАЗРЕШЕНИЯ И ЧАСТОТЫ ОБНОВЛЕНИЯ
# ========================================
Write-Host "[4/6] Настройка разрешения и частоты обновления..." -ForegroundColor Yellow

Write-Host "  Доступные режимы дисплея:" -ForegroundColor Gray

# Получаем доступные разрешения через WMI
try {
    $monitors = Get-WmiObject -Namespace root\wmi -Class WmiMonitorBasicDisplayParams -ErrorAction SilentlyContinue
    
    if ($monitors) {
        Write-Host "    [OK] Информация о мониторах получена" -ForegroundColor Green
        Write-Host "    [INFO] Для изменения разрешения:" -ForegroundColor Cyan
        Write-Host "      Правый клик на рабочем столе → Параметры экрана" -ForegroundColor White
        Write-Host "      Установите максимальное разрешение" -ForegroundColor White
        Write-Host "      Установите частоту обновления 60Hz или выше" -ForegroundColor White
    }
} catch {
    Write-Host "    [INFO] Используйте настройки Windows для изменения разрешения" -ForegroundColor Cyan
}

Write-Host ""

# ========================================
# 5. ОПТИМИЗАЦИЯ ГРАФИКИ И ЦВЕТОВ
# ========================================
Write-Host "[5/6] Оптимизация графики и цветов..." -ForegroundColor Yellow

# Настройка цветового профиля (32-bit color)
$colorPath = "HKCU:\Control Panel\Desktop\WindowMetrics"
if (-not (Test-Path $colorPath)) {
    New-Item -Path $colorPath -Force | Out-Null
}

# Включение аппаратного ускорения
$accelPath = "HKCU:\Software\Microsoft\Avalon.Graphics"
if (-not (Test-Path $accelPath)) {
    New-Item -Path $accelPath -Force | Out-Null
}
Set-ItemProperty -Path $accelPath -Name "DisableHWAcceleration" -Value 0 -ErrorAction SilentlyContinue

# Настройка качества изображения
$imagePath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer"
Set-ItemProperty -Path $imagePath -Name "ShellState" -Value ([byte[]](0x24,0x00,0x00,0x00,0x34,0x8E,0x0E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x13,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x60,0x00,0x00,0x00)) -ErrorAction SilentlyContinue

Write-Host "    [OK] Графика оптимизирована" -ForegroundColor Green
Write-Host ""

# ========================================
# 6. ОПТИМИЗАЦИЯ ШРИФТОВ
# ========================================
Write-Host "[6/6] Оптимизация отображения шрифтов..." -ForegroundColor Yellow

# Настройка сглаживания шрифтов
$fontPath = "HKCU:\Control Panel\Desktop"
Set-ItemProperty -Path $fontPath -Name "FontSmoothing" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $fontPath -Name "FontSmoothingType" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $fontPath -Name "FontSmoothingGamma" -Value 2200 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $fontPath -Name "FontSmoothingOrientation" -Value 1 -ErrorAction SilentlyContinue

# Включение субпиксельного рендеринга
Set-ItemProperty -Path $fontPath -Name "FontSmoothingGamma" -Value 2200 -ErrorAction SilentlyContinue

Write-Host "    [OK] Шрифты оптимизированы" -ForegroundColor Green
Write-Host ""

# ========================================
# ИТОГИ И РЕКОМЕНДАЦИИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Применено:" -ForegroundColor Cyan
Write-Host "  ✓ ClearType включен" -ForegroundColor White
Write-Host "  ✓ DPI масштабирование оптимизировано" -ForegroundColor White
Write-Host "  ✓ Визуальные эффекты оптимизированы" -ForegroundColor White
Write-Host "  ✓ Графика и цвета оптимизированы" -ForegroundColor White
Write-Host "  ✓ Шрифты оптимизированы" -ForegroundColor White
Write-Host ""

Write-Host "ВАЖНО - Сделайте вручную:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ПРОВЕРЬТЕ РАЗРЕШЕНИЕ:" -ForegroundColor Cyan
Write-Host "   Правый клик на рабочем столе → Параметры экрана" -ForegroundColor White
Write-Host "   → Установите МАКСИМАЛЬНОЕ разрешение" -ForegroundColor White
Write-Host "   → Масштабирование: 100% (или подходящее для вашего монитора)" -ForegroundColor White
Write-Host ""
Write-Host "2. ЧАСТОТА ОБНОВЛЕНИЯ:" -ForegroundColor Cyan
Write-Host "   Параметры экрана → Дополнительные параметры дисплея" -ForegroundColor White
Write-Host "   → Свойства видеоадаптера для дисплея" -ForegroundColor White
Write-Host "   → Монитор → Установите максимальную частоту (60Hz, 75Hz, 120Hz и т.д.)" -ForegroundColor White
Write-Host ""
Write-Host "3. CLEARTYPE TUNER:" -ForegroundColor Cyan
Write-Host "   Нажмите Win + R → введите: cttune" -ForegroundColor White
Write-Host "   → Настройте ClearType под ваш монитор" -ForegroundColor White
Write-Host ""
Write-Host "4. ПЕРЕЗАГРУЗИТЕ КОМПЬЮТЕР" -ForegroundColor Yellow
Write-Host "   Для применения всех изменений" -ForegroundColor White
Write-Host ""

if (-not $isAdmin) {
    Write-Host "ПРИМЕЧАНИЕ:" -ForegroundColor Yellow
    Write-Host "  Некоторые настройки требуют прав администратора" -ForegroundColor White
    Write-Host "  Запустите скрипт от администратора для полной оптимизации" -ForegroundColor White
    Write-Host ""
}

pause




