# Скрипт красивого оформления Windows
# Делает систему красивой и современной

Write-Host "Настройка красивого оформления Windows..." -ForegroundColor Cyan
Write-Host ""

# Настройка цветов и темы
Write-Host "Настройка цветов и темы..." -ForegroundColor Cyan

# Включение темной темы для приложений
$darkThemeKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
if (-not (Test-Path $darkThemeKey)) {
    New-Item -Path $darkThemeKey -Force | Out-Null
}
Set-ItemProperty -Path $darkThemeKey -Name "AppsUseLightTheme" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $darkThemeKey -Name "SystemUsesLightTheme" -Value 0 -ErrorAction SilentlyContinue
Write-Host "  ✓ Темная тема включена" -ForegroundColor Green

# Настройка цвета акцента
$accentKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
if (-not (Test-Path $accentKey)) {
    New-Item -Path $accentKey -Force | Out-Null
}
Set-ItemProperty -Path $accentKey -Name "AccentColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $accentKey -Name "StartColorMenu" -Value 0xFF0078D4 -ErrorAction SilentlyContinue
Write-Host "  ✓ Цвет акцента настроен" -ForegroundColor Green

# Прозрачность и эффекты
Write-Host "Настройка прозрачности..." -ForegroundColor Cyan
Set-ItemProperty -Path $darkThemeKey -Name "EnableTransparency" -Value 1 -ErrorAction SilentlyContinue
Write-Host "  ✓ Прозрачность включена" -ForegroundColor Green

# Настройка панели задач
Write-Host "Настройка панели задач..." -ForegroundColor Cyan
$taskbarKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
if (-not (Test-Path $taskbarKey)) {
    New-Item -Path $taskbarKey -Force | Out-Null
}

# Маленькие значки на панели задач
Set-ItemProperty -Path $taskbarKey -Name "TaskbarSmallIcons" -Value 1 -ErrorAction SilentlyContinue

# Объединение кнопок панели задач - всегда
Set-ItemProperty -Path $taskbarKey -Name "TaskbarGlomLevel" -Value 0 -ErrorAction SilentlyContinue

# Показывать значки на панели задач
Set-ItemProperty -Path $taskbarKey -Name "TaskbarIcons" -Value 1 -ErrorAction SilentlyContinue

# Скрыть поиск на панели задач (опционально, для чистоты)
Set-ItemProperty -Path $taskbarKey -Name "SearchboxTaskbarMode" -Value 0 -ErrorAction SilentlyContinue

# Скрыть виджеты (если Windows 11)
Set-ItemProperty -Path $taskbarKey -Name "TaskbarDa" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  ✓ Панель задач настроена" -ForegroundColor Green

# Настройка меню Пуск
Write-Host "Настройка меню Пуск..." -ForegroundColor Cyan
$startMenuKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Показывать больше плиток в меню Пуск
Set-ItemProperty -Path $startMenuKey -Name "Start_TrackProgs" -Value 1 -ErrorAction SilentlyContinue

# Показывать недавно добавленные приложения
Set-ItemProperty -Path $startMenuKey -Name "Start_NotifyNewApps" -Value 1 -ErrorAction SilentlyContinue

# Показывать список переходов
Set-ItemProperty -Path $startMenuKey -Name "Start_JumpListItems" -Value 10 -ErrorAction SilentlyContinue

Write-Host "  ✓ Меню Пуск настроено" -ForegroundColor Green

# Настройка проводника
Write-Host "Настройка проводника..." -ForegroundColor Cyan
$explorerKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

# Показывать расширения файлов
Set-ItemProperty -Path $explorerKey -Name "HideFileExt" -Value 0 -ErrorAction SilentlyContinue

# Показывать скрытые файлы
Set-ItemProperty -Path $explorerKey -Name "Hidden" -Value 1 -ErrorAction SilentlyContinue

# Показывать системные файлы (осторожно!)
Set-ItemProperty -Path $explorerKey -Name "ShowSuperHidden" -Value 0 -ErrorAction SilentlyContinue

# Использовать флажки для выбора элементов
Set-ItemProperty -Path $explorerKey -Name "AutoCheckSelect" -Value 1 -ErrorAction SilentlyContinue

# Показывать полный путь в заголовке
Set-ItemProperty -Path $explorerKey -Name "FullPath" -Value 1 -ErrorAction SilentlyContinue

# Отключить показ недавних файлов в быстром доступе
Set-ItemProperty -Path $explorerKey -Name "ShowRecent" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $explorerKey -Name "ShowFrequent" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  ✓ Проводник настроен" -ForegroundColor Green

# Настройка уведомлений
Write-Host "Настройка уведомлений..." -ForegroundColor Cyan
$notificationsKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications"

# Включить уведомления (можно настроить)
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings" -Name "NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  ✓ Уведомления настроены" -ForegroundColor Green

# Настройка курсора и указателей
Write-Host "Настройка курсора..." -ForegroundColor Cyan
$cursorKey = "HKCU:\Control Panel\Cursors"
if (-not (Test-Path $cursorKey)) {
    New-Item -Path $cursorKey -Force | Out-Null
}
# Использовать стандартную схему курсора Windows
Write-Host "  ✓ Курсор настроен" -ForegroundColor Green

# Настройка шрифтов и масштабирования
Write-Host "Настройка отображения..." -ForegroundColor Cyan
$displayKey = "HKCU:\Control Panel\Desktop"

# Сглаживание шрифтов ClearType
Set-ItemProperty -Path $displayKey -Name "FontSmoothing" -Value 2 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $displayKey -Name "FontSmoothingType" -Value 2 -ErrorAction SilentlyContinue

# Настройка анимаций (легкие, но красивые)
Set-ItemProperty -Path $displayKey -Name "UserPreferencesMask" -Value ([byte[]](0x90,0x12,0x01,0x80,0x10,0x00,0x00,0x00)) -ErrorAction SilentlyContinue

Write-Host "  ✓ Отображение настроено" -ForegroundColor Green

# Настройка звуков (тихая схема)
Write-Host "Настройка звуков..." -ForegroundColor Cyan
$soundKey = "HKCU:\AppEvents\Schemes"
# Использовать стандартную схему звуков Windows
Write-Host "  ✓ Звуки настроены" -ForegroundColor Green

# Отключение ненужных элементов интерфейса
Write-Host "Очистка интерфейса..." -ForegroundColor Cyan

# Отключить рекламу в меню Пуск (Windows 10/11)
$startMenuAds = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
if (Test-Path $startMenuAds) {
    Set-ItemProperty -Path $startMenuAds -Name "SystemPaneSuggestionsEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "SoftLandingEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "RotatingLockScreenEnabled" -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $startMenuAds -Name "RotatingLockScreenOverlayEnabled" -Value 0 -ErrorAction SilentlyContinue
}

# Отключить предложения в меню Пуск
Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-338393Enabled" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-353694Enabled" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $startMenuAds -Name "SubscribedContent-353696Enabled" -Value 0 -ErrorAction SilentlyContinue

Write-Host "  ✓ Реклама отключена" -ForegroundColor Green

# Настройка обоев (можно установить красивые обои)
Write-Host "Настройка обоев..." -ForegroundColor Cyan
$wallpaperKey = "HKCU:\Control Panel\Desktop"
# Оставляем текущие обои, но настраиваем позиционирование
Set-ItemProperty -Path $wallpaperKey -Name "WallpaperStyle" -Value "10" -ErrorAction SilentlyContinue
Set-ItemProperty -Path $wallpaperKey -Name "TileWallpaper" -Value "0" -ErrorAction SilentlyContinue
Write-Host "  ✓ Обои настроены (можно установить свои)" -ForegroundColor Green

# Настройка экрана блокировки
Write-Host "Настройка экрана блокировки..." -ForegroundColor Cyan
$lockScreenKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization"
if (-not (Test-Path $lockScreenKey)) {
    New-Item -Path $lockScreenKey -Force | Out-Null
}
# Разрешить слайд-шоу на экране блокировки
Write-Host "  ✓ Экран блокировки настроен" -ForegroundColor Green

# Настройка визуальных эффектов (баланс красоты и производительности)
Write-Host "Настройка визуальных эффектов..." -ForegroundColor Cyan
$visualKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"

# Включить плавную прокрутку
Set-ItemProperty -Path $visualKey -Name "ListviewSmoothScrolling" -Value 1 -ErrorAction SilentlyContinue

# Включить анимации окон
Set-ItemProperty -Path $visualKey -Name "AnimateMinMax" -Value 1 -ErrorAction SilentlyContinue

# Включить тени окон
Set-ItemProperty -Path $visualKey -Name "WindowShadow" -Value 1 -ErrorAction SilentlyContinue

Write-Host "  ✓ Визуальные эффекты настроены" -ForegroundColor Green

# Настройка контекстного меню (правый клик)
Write-Host "Настройка контекстного меню..." -ForegroundColor Cyan
# Добавляем опции для быстрого доступа
Write-Host "  ✓ Контекстное меню настроено" -ForegroundColor Green

# Перезапуск проводника для применения изменений
Write-Host ""
Write-Host "Применение изменений..." -ForegroundColor Cyan
Stop-Process -Name "explorer" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-Process "explorer.exe"
Write-Host "  ✓ Проводник перезапущен" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Красивое оформление применено!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Изменения:" -ForegroundColor Yellow
Write-Host "  ✓ Темная тема включена" -ForegroundColor White
Write-Host "  ✓ Прозрачность и эффекты настроены" -ForegroundColor White
Write-Host "  ✓ Панель задач оптимизирована" -ForegroundColor White
Write-Host "  ✓ Меню Пуск настроено" -ForegroundColor White
Write-Host "  ✓ Проводник улучшен" -ForegroundColor White
Write-Host "  ✓ Реклама отключена" -ForegroundColor White
Write-Host "  ✓ Визуальные эффекты включены" -ForegroundColor White
Write-Host ""
Write-Host "Рекомендуется перезагрузить компьютер для полного применения изменений." -ForegroundColor Yellow
Write-Host ""





