# Скрипт создания точки восстановления Windows

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ОШИБКА: Скрипт должен быть запущен от имени администратора!" -ForegroundColor Red
    exit 1
}

Write-Host "Создание точки восстановления..." -ForegroundColor Cyan

try {
    $description = "Точка восстановления перед оптимизацией Windows - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Checkpoint-Computer -Description $description -RestorePointType "MODIFY_SETTINGS"
    Write-Host ""
    Write-Host "✓ Точка восстановления успешно создана!" -ForegroundColor Green
    Write-Host "  Описание: $description" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Теперь можно безопасно запускать optimize-windows.ps1" -ForegroundColor Yellow
} catch {
    Write-Host ""
    Write-Host "ОШИБКА: Не удалось создать точку восстановления" -ForegroundColor Red
    Write-Host "Возможные причины:" -ForegroundColor Yellow
    Write-Host "  1. Защита системы отключена" -ForegroundColor White
    Write-Host "  2. Недостаточно места на диске" -ForegroundColor White
    Write-Host "  3. Служба 'Теневое копирование тома' не запущена" -ForegroundColor White
    Write-Host ""
    Write-Host "Попробуйте включить защиту системы вручную:" -ForegroundColor Yellow
    Write-Host "  Панель управления → Система → Защита системы" -ForegroundColor White
}

