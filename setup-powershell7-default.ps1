# Настройка PowerShell 7 как PowerShell по умолчанию
# Run as Administrator (опционально)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Настройка PowerShell 7" -ForegroundColor Cyan
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
Write-Host "ВАРИАНТЫ НАСТРОЙКИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Добавить в PATH (рекомендуется)" -ForegroundColor Cyan
Write-Host "   - PowerShell 7 будет доступен как 'pwsh'" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Настроить терминал по умолчанию" -ForegroundColor Cyan
Write-Host "   - Windows Terminal будет использовать PowerShell 7" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Создать алиас 'powershell' -> 'pwsh'" -ForegroundColor Cyan
Write-Host "   - Команда 'powershell' будет запускать PowerShell 7" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Выберите вариант (1-3) или Enter для выхода"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "[1] Добавление в PATH..." -ForegroundColor Yellow
        
        $pwshPath = (Get-Command pwsh).Source
        $pwshDir = Split-Path $pwshPath -Parent
        
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentPath -notlike "*$pwshDir*") {
            [Environment]::SetEnvironmentVariable("Path", "$currentPath;$pwshDir", "User")
            Write-Host "  [OK] PowerShell 7 добавлен в PATH пользователя" -ForegroundColor Green
            Write-Host "  [INFO] Перезапустите терминал для применения" -ForegroundColor Cyan
        } else {
            Write-Host "  [OK] PowerShell 7 уже в PATH" -ForegroundColor Green
        }
    }
    
    "2" {
        Write-Host ""
        Write-Host "[2] Настройка Windows Terminal..." -ForegroundColor Yellow
        
        $wtSettingsPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_*\LocalState\settings.json"
        $wtSettings = Get-Item $wtSettingsPath -ErrorAction SilentlyContinue
        
        if ($wtSettings) {
            Write-Host "  [OK] Windows Terminal найден" -ForegroundColor Green
            Write-Host "  [INFO] Откройте настройки Windows Terminal (Ctrl+,)" -ForegroundColor Cyan
            Write-Host "  [INFO] Установите PowerShell 7 как профиль по умолчанию" -ForegroundColor Cyan
        } else {
            Write-Host "  [INFO] Windows Terminal не установлен" -ForegroundColor Yellow
            Write-Host "  [INFO] Установите из Microsoft Store" -ForegroundColor Cyan
        }
    }
    
    "3" {
        Write-Host ""
        Write-Host "[3] Создание алиаса..." -ForegroundColor Yellow
        
        # Добавить в профиль PowerShell
        $profilePath = $PROFILE.CurrentUserAllHosts
        $profileDir = Split-Path $profilePath -Parent
        
        if (-not (Test-Path $profileDir)) {
            New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
        }
        
        $aliasLine = "Set-Alias -Name powershell -Value pwsh -Option AllScope -Force"
        
        if (Test-Path $profilePath) {
            $content = Get-Content $profilePath -Raw
            if ($content -notlike "*$aliasLine*") {
                Add-Content -Path $profilePath -Value "`n# PowerShell 7 alias`n$aliasLine"
                Write-Host "  [OK] Алиас добавлен в профиль" -ForegroundColor Green
            } else {
                Write-Host "  [OK] Алиас уже существует" -ForegroundColor Green
            }
        } else {
            Set-Content -Path $profilePath -Value "# PowerShell 7 alias`n$aliasLine"
            Write-Host "  [OK] Профиль создан с алиасом" -ForegroundColor Green
        }
        
        Write-Host "  [INFO] Перезапустите PowerShell для применения" -ForegroundColor Cyan
    }
    
    default {
        Write-Host ""
        Write-Host "[INFO] Выход без изменений" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ГОТОВО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Использование:" -ForegroundColor Cyan
Write-Host "  pwsh                    # Запуск PowerShell 7" -ForegroundColor White
Write-Host "  pwsh --version          # Проверка версии" -ForegroundColor White
Write-Host ""
pause




