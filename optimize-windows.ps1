# Скрипт оптимизации Windows
# Запускать от имени администратора!

param(
    [switch]$Clean,
    [switch]$Performance,
    [switch]$Security,
    [switch]$Beauty,
    [switch]$All
)

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Скрипт должен быть запущен от имени администратора!" -ForegroundColor Red
    Write-Host "Нажмите правой кнопкой на файл и выберите 'Запустить от имени администратора'" -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Оптимизация Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Определяем путь к скриптам
if ($PSScriptRoot) {
    $scriptRoot = $PSScriptRoot
} else {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (-not $scriptRoot) {
        $scriptRoot = Get-Location
    }
}

if ($All -or $Clean) {
    Write-Host "[1/4] Очистка системы..." -ForegroundColor Green
    $cleanScript = Join-Path $scriptRoot "clean-system.ps1"
    if (Test-Path $cleanScript) {
        & $cleanScript
    } else {
        Write-Host "  ОШИБКА: Файл clean-system.ps1 не найден!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Performance) {
    Write-Host "[2/4] Настройка производительности..." -ForegroundColor Green
    $perfScript = Join-Path $scriptRoot "performance-tweaks.ps1"
    if (Test-Path $perfScript) {
        & $perfScript
    } else {
        Write-Host "  ОШИБКА: Файл performance-tweaks.ps1 не найден!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Security) {
    Write-Host "[3/4] Настройка безопасности..." -ForegroundColor Green
    $secScript = Join-Path $scriptRoot "security-tweaks.ps1"
    if (Test-Path $secScript) {
        & $secScript
    } else {
        Write-Host "  ОШИБКА: Файл security-tweaks.ps1 не найден!" -ForegroundColor Red
    }
    Write-Host ""
}

if ($All -or $Beauty) {
    Write-Host "[4/4] Красивое оформление Windows..." -ForegroundColor Green
    $beautyScript = Join-Path $scriptRoot "beauty-tweaks.ps1"
    if (Test-Path $beautyScript) {
        & $beautyScript
    } else {
        Write-Host "  ОШИБКА: Файл beauty-tweaks.ps1 не найден!" -ForegroundColor Red
    }
    Write-Host ""
}

if (-not ($Clean -or $Performance -or $Security -or $Beauty -or $All)) {
    Write-Host "Использование:" -ForegroundColor Yellow
    Write-Host "  .\optimize-windows.ps1 -All              # Все оптимизации + красивое оформление" -ForegroundColor White
    Write-Host "  .\optimize-windows.ps1 -Clean            # Только очистка" -ForegroundColor White
    Write-Host "  .\optimize-windows.ps1 -Performance      # Только производительность" -ForegroundColor White
    Write-Host "  .\optimize-windows.ps1 -Security         # Только безопасность" -ForegroundColor White
    Write-Host "  .\optimize-windows.ps1 -Beauty           # Только красивое оформление" -ForegroundColor White
    exit 0
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Оптимизация завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Рекомендуется перезагрузить компьютер." -ForegroundColor Yellow


