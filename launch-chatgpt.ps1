# Launch ChatGPT Desktop App with Proxy
# This script ensures VPN is running and launches ChatGPT

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Запуск ChatGPT с VPN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check and start Hysteria2
Write-Host "[1/3] Проверка Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (-not $hysteria2) {
    Write-Host "  [WARN] Hysteria2 не запущен, запускаю..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Не найден start-hysteria2.ps1" -ForegroundColor Red
        Write-Host "  [INFO] Запустите Hysteria2 вручную" -ForegroundColor Yellow
        pause
        exit 1
    }
} else {
    Write-Host "  [OK] Hysteria2 работает (PID: $($hysteria2.Id))" -ForegroundColor Green
}

# Step 2: Set environment variables
Write-Host ""
Write-Host "[2/3] Настройка переменных окружения..." -ForegroundColor Yellow
$env:HTTP_PROXY = "http://127.0.0.1:8080"
$env:HTTPS_PROXY = "http://127.0.0.1:8080"
$env:http_proxy = "http://127.0.0.1:8080"
$env:https_proxy = "http://127.0.0.1:8080"
$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"
Write-Host "  [OK] Переменные окружения установлены" -ForegroundColor Green

# Step 3: Launch ChatGPT
Write-Host ""
Write-Host "[3/3] Запуск ChatGPT..." -ForegroundColor Yellow

# Try to find and launch ChatGPT app
$chatgptApp = Get-AppxPackage | Where-Object { $_.Name -like "*chatgpt*" -or $_.Name -like "*openai*" } | Select-Object -First 1

if ($chatgptApp) {
    Write-Host "  [OK] Найдено приложение: $($chatgptApp.Name)" -ForegroundColor Green
    
    # Get the app executable
    $appId = $chatgptApp.PackageFamilyName
    $appName = $chatgptApp.Name
    
    # Try to launch via Start-Process with app ID
    try {
        Write-Host "  [INFO] Запускаю приложение..." -ForegroundColor Gray
        Start-Process "shell:AppsFolder\$appId" -ErrorAction Stop
        Write-Host "  [OK] ChatGPT запущен!" -ForegroundColor Green
    } catch {
        # Alternative: try to launch via explorer
        try {
            Write-Host "  [INFO] Пробую альтернативный способ..." -ForegroundColor Gray
            Start-Process "explorer.exe" -ArgumentList "shell:AppsFolder\$appId" -ErrorAction Stop
            Write-Host "  [OK] ChatGPT запущен!" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Не удалось запустить автоматически" -ForegroundColor Yellow
            Write-Host "  [INFO] Запустите ChatGPT вручную из меню Пуск" -ForegroundColor Gray
            Write-Host ""
            Write-Host "  Или используйте команду:" -ForegroundColor Cyan
            Write-Host "    Start-Process 'shell:AppsFolder\$appId'" -ForegroundColor White
        }
    }
} else {
    Write-Host "  [WARN] Приложение ChatGPT не найдено" -ForegroundColor Yellow
    Write-Host "  [INFO] Запустите ChatGPT вручную из меню Пуск" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Приложение будет использовать:" -ForegroundColor Cyan
    Write-Host "    - Системный прокси (127.0.0.1:8080)" -ForegroundColor White
    Write-Host "    - WinHTTP прокси (для UWP приложений)" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Готово!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ПРОВЕРКА:" -ForegroundColor Yellow
Write-Host "- ChatGPT должен открыться" -ForegroundColor White
Write-Host "- Если не открылся, запустите вручную из меню Пуск" -ForegroundColor White
Write-Host "- Приложение будет использовать VPN автоматически" -ForegroundColor White
Write-Host ""
Write-Host "ЕСЛИ НЕ РАБОТАЕТ:" -ForegroundColor Cyan
Write-Host "1. Проверьте VPN: .\check-vpn.ps1" -ForegroundColor White
Write-Host "2. Перезапустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host "3. Перезагрузите компьютер" -ForegroundColor White
Write-Host ""

# Keep window open for a moment
Start-Sleep -Seconds 2
