# Быстрый запуск оптимизации
# Просто дважды кликните на этот файл

$scriptPath = Join-Path $PSScriptRoot "optimize-windows.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Host "ОШИБКА: Файл optimize-windows.ps1 не найден!" -ForegroundColor Red
    Write-Host "Убедитесь, что все файлы находятся в одной папке." -ForegroundColor Yellow
    pause
    exit 1
}

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Запуск с правами администратора..." -ForegroundColor Yellow
    Write-Host ""
    
    try {
        Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -All" -Wait
    } catch {
        Write-Host "ОШИБКА: Не удалось запустить с правами администратора!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Попробуйте:" -ForegroundColor Yellow
        Write-Host "1. Правой кнопкой на optimize-windows.ps1" -ForegroundColor White
        Write-Host "2. Выберите 'Запустить с PowerShell'" -ForegroundColor White
        Write-Host "3. В PowerShell выполните: .\optimize-windows.ps1 -All" -ForegroundColor White
        Write-Host ""
        pause
    }
} else {
    # Уже запущено от имени администратора
    & $scriptPath -All
}

