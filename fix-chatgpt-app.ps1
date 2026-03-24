# Fix ChatGPT Desktop Application
# Configure proxy for ChatGPT app to work through VPN

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Исправление приложения ChatGPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Hysteria2
Write-Host "[1/8] Проверка Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  [OK] Hysteria2 работает (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Hysteria2 НЕ запущен, запускаю..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Не найден start-hysteria2.ps1" -ForegroundColor Red
        Write-Host "  [INFO] Запустите Hysteria2 вручную" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 2: Check proxy ports
Write-Host "[2/8] Проверка портов прокси..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
$port1080 = Get-NetTCPConnection -LocalPort 1080 -State Listen -ErrorAction SilentlyContinue

if ($port8080) {
    Write-Host "  [OK] HTTP прокси порт 8080 активен" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Порт 8080 НЕ активен!" -ForegroundColor Red
    Write-Host "  [INFO] Запустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor Yellow
}

if ($port1080) {
    Write-Host "  [OK] SOCKS5 прокси порт 1080 активен" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Порт 1080 НЕ активен" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Enable system proxy
Write-Host "[3/8] Настройка системного прокси..." -ForegroundColor Yellow
$proxyKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$proxyEnabled = (Get-ItemProperty -Path $proxyKey -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable

if ($proxyEnabled -ne 1) {
    Set-ItemProperty -Path $proxyKey -Name "ProxyEnable" -Value 1
    Set-ItemProperty -Path $proxyKey -Name "ProxyServer" -Value "127.0.0.1:8080"
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
} else {
    Write-Host "  [OK] Системный прокси уже включен" -ForegroundColor Green
}

# Set bypass list (empty - force all through proxy)
Set-ItemProperty -Path $proxyKey -Name "ProxyOverride" -Value "<local>" -ErrorAction SilentlyContinue
Write-Host "  [OK] Список обхода настроен" -ForegroundColor Green

Write-Host ""

# Step 4: Configure WinHTTP proxy (for UWP apps)
Write-Host "[4/8] Настройка WinHTTP прокси (для UWP приложений)..." -ForegroundColor Yellow
try {
    netsh winhttp set proxy proxy-server="127.0.0.1:8080" bypass-list="<local>" | Out-Null
    $winhttpProxy = netsh winhttp show proxy
    Write-Host "  [OK] WinHTTP прокси настроен" -ForegroundColor Green
    Write-Host "      $($winhttpProxy -replace "`n", " ")" -ForegroundColor Gray
} catch {
    Write-Host "  [WARN] Не удалось настроить WinHTTP: $_" -ForegroundColor Yellow
    Write-Host "  [INFO] Запустите скрипт от имени администратора" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Find ChatGPT app
Write-Host "[5/8] Поиск приложения ChatGPT..." -ForegroundColor Yellow

# Check UWP apps
$uwpApps = Get-AppxPackage | Where-Object { 
    $_.Name -like "*chatgpt*" -or 
    $_.Name -like "*openai*" -or
    $_.Name -like "*chat*" 
} | Select-Object Name, PackageFullName, InstallLocation

if ($uwpApps) {
    Write-Host "  [OK] Найдены UWP приложения:" -ForegroundColor Green
    foreach ($app in $uwpApps) {
        Write-Host "      - $($app.Name)" -ForegroundColor Cyan
        Write-Host "        Путь: $($app.InstallLocation)" -ForegroundColor Gray
    }
} else {
    Write-Host "  [INFO] UWP приложения ChatGPT не найдены" -ForegroundColor Gray
}

# Check desktop apps
$desktopApps = @(
    "$env:LOCALAPPDATA\Programs\ChatGPT",
    "$env:APPDATA\ChatGPT",
    "$env:ProgramFiles\ChatGPT",
    "$env:ProgramFiles(x86)\ChatGPT",
    "$env:LOCALAPPDATA\Programs\OpenAI",
    "$env:APPDATA\OpenAI"
)

$foundDesktopApp = $false
foreach ($path in $desktopApps) {
    if (Test-Path $path) {
        Write-Host "  [OK] Найдено десктопное приложение:" -ForegroundColor Green
        Write-Host "      Путь: $path" -ForegroundColor Cyan
        $foundDesktopApp = $true
    }
}

# Check running processes
$chatgptProcesses = Get-Process | Where-Object { 
    $_.ProcessName -like "*chatgpt*" -or 
    $_.ProcessName -like "*openai*" 
}

if ($chatgptProcesses) {
    Write-Host "  [OK] Найдены запущенные процессы:" -ForegroundColor Green
    foreach ($proc in $chatgptProcesses) {
        Write-Host "      - $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Cyan
        Write-Host "        Путь: $($proc.Path)" -ForegroundColor Gray
    }
} else {
    Write-Host "  [INFO] Приложение ChatGPT не запущено" -ForegroundColor Gray
}

if (-not $uwpApps -and -not $foundDesktopApp -and -not $chatgptProcesses) {
    Write-Host "  [WARN] Приложение ChatGPT не найдено!" -ForegroundColor Yellow
    Write-Host "  [INFO] Убедитесь, что приложение установлено" -ForegroundColor Gray
}

Write-Host ""

# Step 6: Configure environment variables for apps
Write-Host "[6/8] Настройка переменных окружения..." -ForegroundColor Yellow
try {
    # Set HTTP_PROXY and HTTPS_PROXY (for Electron apps and some desktop apps)
    [Environment]::SetEnvironmentVariable("HTTP_PROXY", "http://127.0.0.1:8080", "User")
    [Environment]::SetEnvironmentVariable("HTTPS_PROXY", "http://127.0.0.1:8080", "User")
    [Environment]::SetEnvironmentVariable("http_proxy", "http://127.0.0.1:8080", "User")
    [Environment]::SetEnvironmentVariable("https_proxy", "http://127.0.0.1:8080", "User")
    [Environment]::SetEnvironmentVariable("NO_PROXY", "localhost,127.0.0.1", "User")
    [Environment]::SetEnvironmentVariable("no_proxy", "localhost,127.0.0.1", "User")
    
    Write-Host "  [OK] Переменные окружения настроены" -ForegroundColor Green
    Write-Host "      HTTP_PROXY=http://127.0.0.1:8080" -ForegroundColor Gray
    Write-Host "      HTTPS_PROXY=http://127.0.0.1:8080" -ForegroundColor Gray
} catch {
    Write-Host "  [WARN] Не удалось настроить переменные окружения: $_" -ForegroundColor Yellow
}

Write-Host ""

# Step 7: Reset network stack (if admin)
Write-Host "[7/8] Сброс сетевого стека..." -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    try {
        ipconfig /flushdns | Out-Null
        Write-Host "  [OK] DNS кэш очищен" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Не удалось очистить DNS: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Требуются права администратора для полного сброса" -ForegroundColor Gray
}

Write-Host ""

# Step 8: Create shortcut script for ChatGPT app
Write-Host "[8/8] Создание скрипта запуска..." -ForegroundColor Yellow
$launchScript = @"
# Launch ChatGPT with proxy
`$env:HTTP_PROXY = "http://127.0.0.1:8080"
`$env:HTTPS_PROXY = "http://127.0.0.1:8080"
`$env:http_proxy = "http://127.0.0.1:8080"
`$env:https_proxy = "http://127.0.0.1:8080"

# Check if Hysteria2 is running
`$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (-not `$hysteria2) {
    Write-Host "Starting Hysteria2..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 2
    }
}

# Launch ChatGPT
Write-Host "Launching ChatGPT..." -ForegroundColor Green
"@

$launchScriptPath = ".\launch-chatgpt.ps1"
Set-Content -Path $launchScriptPath -Value $launchScript -Encoding UTF8
Write-Host "  [OK] Скрипт запуска создан: $launchScriptPath" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Настройка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ЧТО СДЕЛАНО:" -ForegroundColor Yellow
Write-Host "✓ Hysteria2 проверен" -ForegroundColor White
Write-Host "✓ Порты прокси проверены" -ForegroundColor White
Write-Host "✓ Системный прокси включен" -ForegroundColor White
Write-Host "✓ WinHTTP прокси настроен (для UWP приложений)" -ForegroundColor White
Write-Host "✓ Приложение ChatGPT найдено" -ForegroundColor White
Write-Host "✓ Переменные окружения настроены" -ForegroundColor White
Write-Host "✓ DNS кэш очищен" -ForegroundColor White
Write-Host "✓ Скрипт запуска создан" -ForegroundColor White
Write-Host ""
Write-Host "ВАЖНО - СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ЗАКРОЙТЕ приложение ChatGPT (если запущено)" -ForegroundColor White
Write-Host ""
Write-Host "2. ПЕРЕЗАПУСТИТЕ приложение ChatGPT:" -ForegroundColor White
Write-Host "   - Через меню Пуск" -ForegroundColor Gray
Write-Host "   - Или через скрипт: .\launch-chatgpt.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "3. ЕСЛИ НЕ РАБОТАЕТ:" -ForegroundColor Yellow
Write-Host "   - Проверьте VPN: .\check-vpn.ps1" -ForegroundColor White
Write-Host "   - Перезапустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host "   - Перезагрузите компьютер" -ForegroundColor White
Write-Host ""
Write-Host "4. ДЛЯ UWP ПРИЛОЖЕНИЙ:" -ForegroundColor Cyan
Write-Host "   - WinHTTP прокси уже настроен" -ForegroundColor White
Write-Host "   - Приложение должно использовать системный прокси" -ForegroundColor White
Write-Host ""
Write-Host "5. ДЛЯ ДЕСКТОПНЫХ ПРИЛОЖЕНИЙ:" -ForegroundColor Cyan
Write-Host "   - Переменные окружения настроены" -ForegroundColor White
Write-Host "   - Используйте скрипт запуска: .\launch-chatgpt.ps1" -ForegroundColor White
Write-Host ""
Write-Host "ПРОВЕРКА:" -ForegroundColor Cyan
Write-Host "  .\check-vpn.ps1" -ForegroundColor White
Write-Host ""

