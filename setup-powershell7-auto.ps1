# Автоматическая настройка PowerShell 7
# Применяет все настройки автоматически

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Автоматическая настройка PowerShell 7" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка версии
$ps7Version = pwsh --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] PowerShell 7 установлен: $ps7Version" -ForegroundColor Green
} else {
    Write-Host "[ERROR] PowerShell 7 не найден!" -ForegroundColor Red
    Write-Host "[INFO] Установите с: https://aka.ms/PSWindows" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""

# 1. Добавление в PATH
Write-Host "[1/3] Добавление PowerShell 7 в PATH..." -ForegroundColor Yellow

$pwshPath = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if ($pwshPath) {
    $pwshDir = Split-Path $pwshPath -Parent
    
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$pwshDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pwshDir", "User")
        Write-Host "  [OK] PowerShell 7 добавлен в PATH пользователя" -ForegroundColor Green
        Write-Host "  [INFO] Перезапустите терминал для применения" -ForegroundColor Cyan
    } else {
        Write-Host "  [OK] PowerShell 7 уже в PATH" -ForegroundColor Green
    }
} else {
    Write-Host "  [WARN] Не удалось найти путь к PowerShell 7" -ForegroundColor Yellow
}

Write-Host ""

# 2. Создание алиаса в профиле
Write-Host "[2/3] Создание алиаса 'powershell' -> 'pwsh'..." -ForegroundColor Yellow

$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath -Parent

if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Host "  [OK] Создана папка профиля" -ForegroundColor Green
}

$aliasLine = "Set-Alias -Name powershell -Value pwsh -Option AllScope -Force -ErrorAction SilentlyContinue"

if (Test-Path $profilePath) {
    $content = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
    if ($content -and $content -notlike "*Set-Alias -Name powershell*") {
        Add-Content -Path $profilePath -Value "`n# PowerShell 7 alias`n$aliasLine"
        Write-Host "  [OK] Алиас добавлен в существующий профиль" -ForegroundColor Green
    } elseif ($content -and $content -like "*Set-Alias -Name powershell*") {
        Write-Host "  [OK] Алиас уже существует в профиле" -ForegroundColor Green
    } else {
        Set-Content -Path $profilePath -Value "# PowerShell 7 alias`n$aliasLine"
        Write-Host "  [OK] Профиль создан с алиасом" -ForegroundColor Green
    }
} else {
    Set-Content -Path $profilePath -Value "# PowerShell 7 alias`n$aliasLine"
    Write-Host "  [OK] Профиль создан с алиасом" -ForegroundColor Green
}

Write-Host "  [INFO] Профиль: $profilePath" -ForegroundColor Gray
Write-Host ""

# 3. Информация о Windows Terminal
Write-Host "[3/3] Информация о Windows Terminal..." -ForegroundColor Yellow

$wtSettingsPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json"
$wtSettings = Get-Item $wtSettingsPath -ErrorAction SilentlyContinue

if ($wtSettings) {
    Write-Host "  [OK] Windows Terminal найден" -ForegroundColor Green
    Write-Host "  [INFO] Для настройки PowerShell 7 по умолчанию:" -ForegroundColor Cyan
    Write-Host "    1. Откройте Windows Terminal" -ForegroundColor White
    Write-Host "    2. Нажмите Ctrl+, (настройки)" -ForegroundColor White
    Write-Host "    3. Выберите 'PowerShell' как профиль по умолчанию" -ForegroundColor White
} else {
    Write-Host "  [INFO] Windows Terminal не установлен" -ForegroundColor Yellow
    Write-Host "  [INFO] Установите из Microsoft Store (опционально)" -ForegroundColor Cyan
}

Write-Host ""

# Итоги
Write-Host "========================================" -ForegroundColor Green
Write-Host "  НАСТРОЙКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Применено:" -ForegroundColor Cyan
Write-Host "  ✓ PowerShell 7 добавлен в PATH" -ForegroundColor White
Write-Host "  ✓ Создан алиас 'powershell' -> 'pwsh'" -ForegroundColor White
Write-Host ""
Write-Host "Следующие шаги:" -ForegroundColor Yellow
Write-Host "  1. Перезапустите PowerShell/терминал" -ForegroundColor White
Write-Host "  2. Проверьте: pwsh --version" -ForegroundColor White
Write-Host "  3. После перезапуска: powershell --version (должен показать 7.5.4)" -ForegroundColor White
Write-Host ""
Write-Host "Использование:" -ForegroundColor Cyan
Write-Host "  pwsh                    # Запуск PowerShell 7" -ForegroundColor Gray
Write-Host "  powershell              # После перезапуска тоже будет PowerShell 7" -ForegroundColor Gray
Write-Host ""




