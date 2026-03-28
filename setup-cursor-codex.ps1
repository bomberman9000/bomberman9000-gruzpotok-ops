# Настройка ChatGPT Codex в Cursor
# Этот скрипт добавляет настройки для Codex в Cursor

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  НАСТРОЙКА CHATGPT CODEX В CURSOR" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Путь к настройкам Cursor
$cursorSettingsPath = "$env:APPDATA\Cursor\User\settings.json"

Write-Host "[1/4] Проверка Cursor..." -ForegroundColor Yellow

# Проверка, установлен ли Cursor
$cursorInstalled = Test-Path $cursorSettingsPath

if (-not $cursorInstalled) {
    Write-Host "  [WARN] Cursor settings не найдены" -ForegroundColor Yellow
    Write-Host "  [INFO] Путь: $cursorSettingsPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Возможные причины:" -ForegroundColor Cyan
    Write-Host "  1. Cursor не установлен" -ForegroundColor White
    Write-Host "  2. Cursor еще не запускался" -ForegroundColor White
    Write-Host "  3. Настройки в другом месте" -ForegroundColor White
    Write-Host ""
    Write-Host "  РЕШЕНИЕ:" -ForegroundColor Cyan
    Write-Host "  1. Запустите Cursor хотя бы один раз" -ForegroundColor White
    Write-Host "  2. Затем запустите этот скрипт снова" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "  [OK] Cursor найден" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] Чтение текущих настроек..." -ForegroundColor Yellow

# Чтение текущих настроек
try {
    $settingsContent = Get-Content -Path $cursorSettingsPath -Raw -ErrorAction Stop
    $settings = $settingsContent | ConvertFrom-Json -ErrorAction Stop
    Write-Host "  [OK] Настройки прочитаны" -ForegroundColor Green
} catch {
    # Если файл пустой или невалидный JSON, создаем новый
    Write-Host "  [INFO] Создание новых настроек..." -ForegroundColor Yellow
    $settings = @{} | ConvertTo-Json
    $settingsContent = "{}"
    $settings = $settingsContent | ConvertFrom-Json
}

Write-Host ""

Write-Host "[3/4] Добавление настроек Codex..." -ForegroundColor Yellow

# Добавление настроек Codex
$settings | Add-Member -MemberType NoteProperty -Name "cursor.aiModel" -Value "gpt-4-codex" -Force -ErrorAction SilentlyContinue
$settings | Add-Member -MemberType NoteProperty -Name "cursor.chatModel" -Value "gpt-4-codex" -Force -ErrorAction SilentlyContinue
$settings | Add-Member -MemberType NoteProperty -Name "cursor.composerModel" -Value "gpt-4-codex" -Force -ErrorAction SilentlyContinue

# Если нужно добавить API ключ (пользователь должен ввести сам)
Write-Host "  [INFO] Настройки Codex добавлены" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] Сохранение настроек..." -ForegroundColor Yellow

# Сохранение настроек
try {
    $settingsJson = $settings | ConvertTo-Json -Depth 10
    # Форматирование JSON для читаемости
    $settingsJson = $settingsJson -replace '",', '",' -replace '":', '": '
    
    # Создание резервной копии
    $backupPath = "$cursorSettingsPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item -Path $cursorSettingsPath -Destination $backupPath -ErrorAction SilentlyContinue
    Write-Host "  [OK] Резервная копия создана: $backupPath" -ForegroundColor Gray
    
    # Сохранение новых настроек
    Set-Content -Path $cursorSettingsPath -Value $settingsJson -Encoding UTF8 -ErrorAction Stop
    Write-Host "  [OK] Настройки сохранены" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Не удалось сохранить настройки" -ForegroundColor Red
    Write-Host "  Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  РЕШЕНИЕ:" -ForegroundColor Cyan
    Write-Host "  Добавьте вручную в settings.json:" -ForegroundColor White
    Write-Host '    "cursor.aiModel": "gpt-4-codex",' -ForegroundColor Gray
    Write-Host '    "cursor.chatModel": "gpt-4-codex",' -ForegroundColor Gray
    Write-Host '    "cursor.composerModel": "gpt-4-codex"' -ForegroundColor Gray
    exit 1
}

Write-Host ""

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅ НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""

Write-Host "📋 ЧТО ДАЛЬШЕ:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. ДОБАВЬТЕ API КЛЮЧ OPENAI:" -ForegroundColor Yellow
Write-Host "   • Откройте Cursor" -ForegroundColor White
Write-Host "   • Нажмите Ctrl + , (настройки)" -ForegroundColor White
Write-Host "   • Найдите 'OpenAI API Key'" -ForegroundColor White
Write-Host "   • Введите ваш ключ с https://platform.openai.com/api-keys" -ForegroundColor White
Write-Host ""
Write-Host "2. ПРОВЕРЬТЕ МОДЕЛЬ:" -ForegroundColor Yellow
Write-Host "   • Ctrl + Shift + P" -ForegroundColor White
Write-Host "   • Введите: 'Select Model'" -ForegroundColor White
Write-Host "   • Выберите 'gpt-4-codex' или другую модель Codex" -ForegroundColor White
Write-Host ""
Write-Host "3. ПЕРЕЗАПУСТИТЕ CURSOR:" -ForegroundColor Yellow
Write-Host "   • Закройте и откройте Cursor заново" -ForegroundColor White
Write-Host "   • Настройки применятся автоматически" -ForegroundColor White
Write-Host ""

Write-Host "📄 Подробная инструкция: ДОБАВИТЬ_CHATGPT_CODEX.txt" -ForegroundColor Cyan
Write-Host ""

# Предложение открыть настройки Cursor (только в интерактивном режиме)
if ([Environment]::UserInteractive) {
    try {
        $openSettings = Read-Host "Открыть папку с настройками Cursor? (Y/N)"
        if ($openSettings -eq "Y" -or $openSettings -eq "y") {
            $settingsFolder = Split-Path -Path $cursorSettingsPath -Parent
            Start-Process explorer.exe -ArgumentList $settingsFolder
            Write-Host ""
            Write-Host "  [INFO] Папка открыта" -ForegroundColor Green
        }
    } catch {
        # Игнорируем ошибку в неинтерактивном режиме
    }
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Gray
Write-Host ""
