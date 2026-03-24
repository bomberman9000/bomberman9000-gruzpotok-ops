# Быстрый запуск всех оптимизаций
# Запускать от имени администратора!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ЗАПУСК ПОЛНОЙ ОПТИМИЗАЦИИ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Требуются права администратора!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Запустите PowerShell от имени администратора:" -ForegroundColor Yellow
    Write-Host "  1. Win + X" -ForegroundColor White
    Write-Host "  2. Windows PowerShell (администратор)" -ForegroundColor White
    Write-Host "  3. Затем выполните: .\run-all.ps1" -ForegroundColor White
    Write-Host ""
    pause
    exit 1
}

# Переход в папку скрипта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Запуск полной оптимизации..." -ForegroundColor Green
Write-Host ""

# Запуск главного скрипта
& ".\optimize-windows.ps1" -All

Write-Host ""
Write-Host "Готово! Рекомендуется перезагрузка." -ForegroundColor Yellow
Write-Host ""
pause





