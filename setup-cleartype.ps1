# Быстрая настройка ClearType для четкости текста

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  НАСТРОЙКА CLEARTYPE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Запускаю ClearType Tuner..." -ForegroundColor Yellow
Write-Host ""

# Запуск ClearType Tuner
Start-Process "cttune.exe"

Write-Host "[OK] ClearType Tuner открыт" -ForegroundColor Green
Write-Host ""
Write-Host "ИНСТРУКЦИЯ:" -ForegroundColor Cyan
Write-Host "  1. Выберите монитор (если несколько)" -ForegroundColor White
Write-Host "  2. Выберите наиболее четкий текст на каждом шаге" -ForegroundColor White
Write-Host "  3. Завершите настройку" -ForegroundColor White
Write-Host ""
Write-Host "Это улучшит четкость текста и уберет пикселизацию!" -ForegroundColor Green
Write-Host ""




