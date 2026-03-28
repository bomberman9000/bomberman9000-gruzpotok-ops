# Быстрая настройка ClearType для четкости текста

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  НАСТРОЙКА CLEARTYPE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Запускаю ClearType Tuner..." -ForegroundColor Yellow
Write-Host ""

# Проверка наличия ClearType Tuner
$cttunePaths = @(
    "$env:SystemRoot\System32\cttune.exe",
    "$env:SystemRoot\SysWOW64\cttune.exe",
    "cttune.exe"
)

$cttuneExe = $null
foreach ($path in $cttunePaths) {
    if (Test-Path $path) {
        $cttuneExe = $path
        break
    }
}

if ($cttuneExe) {
    try {
        Start-Process $cttuneExe -ErrorAction Stop
        Write-Host "[OK] ClearType Tuner открыт" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Не удалось запустить ClearType Tuner: $_" -ForegroundColor Red
        Write-Host "[INFO] Попробуйте запустить вручную:" -ForegroundColor Yellow
        Write-Host "      $cttuneExe" -ForegroundColor White
        exit 1
    }
} else {
    Write-Host "[ERROR] ClearType Tuner не найден на системе" -ForegroundColor Red
    Write-Host "[INFO] Попробуйте альтернативные способы:" -ForegroundColor Yellow
    Write-Host "      1. Откройте Настройки Windows > Система > Экран > Дополнительные параметры масштабирования" -ForegroundColor White
    Write-Host "      2. Или используйте: Настройки > Персонализация > Шрифты > Настройки ClearType" -ForegroundColor White
    Write-Host ""
    Write-Host "      Или выполните в PowerShell:" -ForegroundColor Cyan
    Write-Host "      control /name Microsoft.Display" -ForegroundColor White
    exit 1
}
Write-Host ""
Write-Host "ИНСТРУКЦИЯ:" -ForegroundColor Cyan
Write-Host "  1. Выберите монитор (если несколько)" -ForegroundColor White
Write-Host "  2. Выберите наиболее четкий текст на каждом шаге" -ForegroundColor White
Write-Host "  3. Завершите настройку" -ForegroundColor White
Write-Host ""
Write-Host "Это улучшит четкость текста и уберет пикселизацию!" -ForegroundColor Green
Write-Host ""




