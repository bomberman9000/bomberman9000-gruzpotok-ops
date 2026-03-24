# Быстрая настройка без прав администратора
# Применяет только те настройки, которые не требуют админских прав

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  БЫСТРАЯ НАСТРОЙКА (БЕЗ АДМИНА)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INFO] Эти настройки НЕ требуют прав администратора" -ForegroundColor Yellow
Write-Host ""

$changes = 0

# ========================================
# ПРОВОДНИК
# ========================================
Write-Host "[1/5] Настройка Проводника..." -ForegroundColor Yellow

$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Показывать скрытые файлы
Set-ItemProperty -Path $explorerKey -Name "Hidden" -Value 1
$changes++

# Показывать расширения файлов
Set-ItemProperty -Path $explorerKey -Name "HideFileExt" -Value 0
$changes++

# Открывать на "Этот компьютер"
Set-ItemProperty -Path $explorerKey -Name "LaunchTo" -Value 1
$changes++

# Компактный вид
Set-ItemProperty -Path $explorerKey -Name "UseCompactMode" -Value 1 -Force
$changes++

# Отключить недавние файлы
Set-ItemProperty -Path $explorerKey -Name "ShowRecent" -Value 0
Set-ItemProperty -Path $explorerKey -Name "ShowFrequent" -Value 0
$changes++

Write-Host "  [OK] Проводник настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# ПАНЕЛЬ ЗАДАЧ
# ========================================
Write-Host "[2/5] Настройка панели задач..." -ForegroundColor Yellow

# Выравнивание по левому краю
Set-ItemProperty -Path $explorerKey -Name "TaskbarAl" -Value 0
$changes++

# Отключить поиск
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Search" -Name "SearchboxTaskbarMode" -Value 0
$changes++

# Отключить виджеты
Set-ItemProperty -Path $explorerKey -Name "TaskbarDa" -Value 0
$changes++

# Отключить чат
Set-ItemProperty -Path $explorerKey -Name "TaskbarMn" -Value 0
$changes++

# Показывать все значки в трее
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer" -Name "EnableAutoTray" -Value 0
$changes++

Write-Host "  [OK] Панель задач настроена" -ForegroundColor Green
Write-Host ""

# ========================================
# КОНФИДЕНЦИАЛЬНОСТЬ
# ========================================
Write-Host "[3/5] Отключение рекламы..." -ForegroundColor Yellow

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
    $changes++
}

Write-Host "  [OK] Реклама отключена" -ForegroundColor Green
Write-Host ""

# ========================================
# ДИСПЛЕЙ
# ========================================
Write-Host "[4/5] Настройка дисплея..." -ForegroundColor Yellow

# ClearType
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothing" -Value 2
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "FontSmoothingType" -Value 2
$changes++

# Аппаратное ускорение
$avalonKey = "HKCU:\Software\Microsoft\Avalon.Graphics"
if (-not (Test-Path $avalonKey)) {
    New-Item -Path $avalonKey -Force | Out-Null
}
Set-ItemProperty -Path $avalonKey -Name "DisableHWAcceleration" -Value 0
$changes++

# Темная тема
$themeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
Set-ItemProperty -Path $themeKey -Name "AppsUseLightTheme" -Value 0
Set-ItemProperty -Path $themeKey -Name "SystemUsesLightTheme" -Value 0
$changes++

Write-Host "  [OK] Дисплей настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# ИГРОВОЙ РЕЖИМ
# ========================================
Write-Host "[5/5] Настройка игрового режима..." -ForegroundColor Yellow

# Отключить Game DVR
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR" -Name "AppCaptureEnabled" -Value 0
Set-ItemProperty -Path "HKCU:\System\GameConfigStore" -Name "GameDVR_Enabled" -Value 0
$changes++

# Включить игровой режим
Set-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled" -Value 1
$changes++

Write-Host "  [OK] Игровой режим настроен" -ForegroundColor Green
Write-Host ""

# ========================================
# ПЕРЕЗАПУСК EXPLORER
# ========================================
Write-Host "Перезапуск Проводника..." -ForegroundColor Yellow
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "  [OK] Проводник перезапущен" -ForegroundColor Green
Write-Host ""

# ========================================
# ИТОГИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  БЫСТРАЯ НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "ПРИМЕНЕНО ИЗМЕНЕНИЙ: $changes" -ForegroundColor Cyan
Write-Host ""

Write-Host "ЧТО НАСТРОЕНО:" -ForegroundColor Yellow
Write-Host "  ✓ Проводник (показывать всё)" -ForegroundColor Green
Write-Host "  ✓ Панель задач (слева, без лишнего)" -ForegroundColor Green
Write-Host "  ✓ Реклама отключена" -ForegroundColor Green
Write-Host "  ✓ Дисплей (ClearType, темная тема)" -ForegroundColor Green
Write-Host "  ✓ Игровой режим включен" -ForegroundColor Green
Write-Host ""

Write-Host "ДЛЯ ПОЛНОЙ НАСТРОЙКИ:" -ForegroundColor Yellow
Write-Host "  Запустите PowerShell от администратора:" -ForegroundColor White
Write-Host "  .\setup-admin.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Это даст:" -ForegroundColor White
Write-Host "  • Оптимизацию производительности" -ForegroundColor Gray
Write-Host "  • Отключение телеметрии" -ForegroundColor Gray
Write-Host "  • Оптимизацию служб" -ForegroundColor Gray
Write-Host "  • Настройку безопасности" -ForegroundColor Gray
Write-Host "  • Очистку системы (~35 GB)" -ForegroundColor Gray
Write-Host ""

pause
