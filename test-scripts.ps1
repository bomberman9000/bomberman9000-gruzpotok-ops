# Тестирование скриптов оптимизации Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ПРОВЕРКА СКРИПТОВ ОПТИМИЗАЦИИ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) {
    $scriptRoot = Get-Location
}

$allOk = $true

# Проверка наличия файлов
Write-Host "[1/4] Проверка наличия файлов..." -ForegroundColor Yellow
$requiredFiles = @(
    "optimize-windows.ps1",
    "clean-system.ps1",
    "performance-tweaks.ps1",
    "security-tweaks.ps1"
)

foreach ($file in $requiredFiles) {
    $path = Join-Path $scriptRoot $file
    if (Test-Path $path) {
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $file - НЕ НАЙДЕН!" -ForegroundColor Red
        $allOk = $false
    }
}

# Проверка синтаксиса PowerShell
Write-Host ""
Write-Host "[2/4] Проверка синтаксиса..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    $path = Join-Path $scriptRoot $file
    if (Test-Path $path) {
        try {
            $null = [System.Management.Automation.PSParser]::Tokenize((Get-Content $path -Raw -ErrorAction Stop), [ref]$null)
            Write-Host "  [OK] $file - синтаксис корректен" -ForegroundColor Green
        } catch {
            Write-Host "  [FAIL] $file - ошибка синтаксиса: $($_.Exception.Message)" -ForegroundColor Red
            $allOk = $false
        }
    }
}

# Проверка путей в главном скрипте
Write-Host ""
Write-Host "[3/4] Проверка путей к скриптам..." -ForegroundColor Yellow
$mainScript = Join-Path $scriptRoot "optimize-windows.ps1"
if (Test-Path $mainScript) {
    $content = Get-Content $mainScript -Raw
    foreach ($file in @("clean-system.ps1", "performance-tweaks.ps1", "security-tweaks.ps1")) {
        if ($content -match $file) {
            $testPath = Join-Path $scriptRoot $file
            if (Test-Path $testPath) {
                Write-Host "  [OK] Путь к $file корректен" -ForegroundColor Green
            } else {
                Write-Host "  [FAIL] Путь к $file не найден" -ForegroundColor Red
                $allOk = $false
            }
        }
    }
}

# Проверка прав администратора
Write-Host ""
Write-Host "[4/4] Проверка прав доступа..." -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "  [OK] Запущено от имени администратора" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Не запущено от имени администратора (это нормально для теста)" -ForegroundColor Yellow
    Write-Host "  [INFO] Для выполнения оптимизации потребуются права администратора" -ForegroundColor Yellow
}

# Итог
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allOk) {
    Write-Host "  ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!" -ForegroundColor Green
    Write-Host "  Скрипты готовы к использованию." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Для запуска оптимизации:" -ForegroundColor Yellow
    Write-Host "  1. Дважды кликните на 'Оптимизация Windows.lnk'" -ForegroundColor White
    Write-Host "  2. Или запустите: .\optimize-windows.ps1 -All" -ForegroundColor White
    Write-Host "     (от имени администратора)" -ForegroundColor White
} else {
    Write-Host "  ОБНАРУЖЕНЫ ПРОБЛЕМЫ!" -ForegroundColor Red
    Write-Host "  Проверьте ошибки выше." -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

