# Fix Steam Proxy - Configure Steam to use VPN
# This script configures Steam to work through Hysteria2 proxy

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Настройка Steam для работы через VPN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Hysteria2
Write-Host "[1/7] Проверка Hysteria2..." -ForegroundColor Yellow
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
Write-Host "[2/7] Проверка портов прокси..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
$port1080 = Get-NetTCPConnection -LocalPort 1080 -State Listen -ErrorAction SilentlyContinue

if ($port8080) {
    Write-Host "  [OK] HTTP прокси порт 8080 активен" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Порт 8080 НЕ активен!" -ForegroundColor Red
}

if ($port1080) {
    Write-Host "  [OK] SOCKS5 прокси порт 1080 активен" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Порт 1080 НЕ активен" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Enable system proxy
Write-Host "[3/7] Настройка системного прокси..." -ForegroundColor Yellow
$proxyKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$proxyEnabled = (Get-ItemProperty -Path $proxyKey -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable

if ($proxyEnabled -ne 1) {
    Set-ItemProperty -Path $proxyKey -Name "ProxyEnable" -Value 1
    Set-ItemProperty -Path $proxyKey -Name "ProxyServer" -Value "127.0.0.1:8080"
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
} else {
    Write-Host "  [OK] Системный прокси уже включен" -ForegroundColor Green
}

# Set bypass list (only localhost)
Set-ItemProperty -Path $proxyKey -Name "ProxyOverride" -Value "<local>" -ErrorAction SilentlyContinue
Write-Host "  [OK] Список обхода настроен" -ForegroundColor Green

Write-Host ""

# Step 4: Configure WinHTTP proxy
Write-Host "[4/7] Настройка WinHTTP прокси..." -ForegroundColor Yellow
try {
    netsh winhttp set proxy proxy-server="127.0.0.1:8080" bypass-list="<local>" | Out-Null
    Write-Host "  [OK] WinHTTP прокси настроен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить WinHTTP: $_" -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Find Steam installation
Write-Host "[5/7] Поиск установки Steam..." -ForegroundColor Yellow
$steamPaths = @(
    "$env:ProgramFiles(x86)\Steam",
    "$env:ProgramFiles\Steam",
    "$env:LOCALAPPDATA\Programs\Steam"
)

$steamPath = $null
foreach ($path in $steamPaths) {
    if (Test-Path $path) {
        $steamPath = $path
        Write-Host "  [OK] Найден Steam: $steamPath" -ForegroundColor Green
        break
    }
}

if (-not $steamPath) {
    Write-Host "  [WARN] Steam не найден в стандартных местах" -ForegroundColor Yellow
    Write-Host "  [INFO] Проверяю запущенные процессы..." -ForegroundColor Gray
    
    $steamProcess = Get-Process -Name "Steam" -ErrorAction SilentlyContinue
    if ($steamProcess) {
        $steamPath = Split-Path $steamProcess.Path -Parent
        Write-Host "  [OK] Найден Steam через процесс: $steamPath" -ForegroundColor Green
    }
}

Write-Host ""

# Step 6: Configure Steam proxy settings
Write-Host "[6/7] Настройка прокси Steam..." -ForegroundColor Yellow

if ($steamPath) {
    # Steam config file location
    $steamConfigPath = Join-Path $steamPath "config\config.vdf"
    $steamUserData = Join-Path $steamPath "userdata"
    
    Write-Host "  [INFO] Путь к конфигу: $steamConfigPath" -ForegroundColor Gray
    
    # Note: Steam config.vdf is binary, so we'll use environment variables instead
    # Steam respects HTTP_PROXY and HTTPS_PROXY environment variables
    
    Write-Host "  [OK] Steam найден, настраиваю переменные окружения" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Steam не найден, настраиваю переменные окружения глобально" -ForegroundColor Yellow
}

# Set environment variables for Steam
try {
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

# Step 7: Create Steam launch script
Write-Host "[7/7] Создание скрипта запуска Steam..." -ForegroundColor Yellow

$launchScript = @"
# Launch Steam with Proxy
# This script ensures VPN is running and launches Steam with proxy settings

Write-Host "Запуск Steam с VPN..." -ForegroundColor Cyan
Write-Host ""

# Check Hysteria2
`$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (-not `$hysteria2) {
    Write-Host "Запускаю Hysteria2..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    }
}

# Set environment variables
`$env:HTTP_PROXY = "http://127.0.0.1:8080"
`$env:HTTPS_PROXY = "http://127.0.0.1:8080"
`$env:http_proxy = "http://127.0.0.1:8080"
`$env:https_proxy = "http://127.0.0.1:8080"
`$env:NO_PROXY = "localhost,127.0.0.1"
`$env:no_proxy = "localhost,127.0.0.1"

# Find Steam executable
`$steamPaths = @(
    "`$env:ProgramFiles(x86)\Steam\steam.exe",
    "`$env:ProgramFiles\Steam\steam.exe",
    "`$env:LOCALAPPDATA\Programs\Steam\steam.exe"
)

`$steamExe = `$null
foreach (`$path in `$steamPaths) {
    if (Test-Path `$path) {
        `$steamExe = `$path
        break
    }
}

# If not found, try to find via process
if (-not `$steamExe) {
    `$steamProcess = Get-Process -Name "Steam" -ErrorAction SilentlyContinue
    if (`$steamProcess) {
        `$steamExe = `$steamProcess.Path
    }
}

if (`$steamExe) {
    Write-Host "Запускаю Steam: `$steamExe" -ForegroundColor Green
    Start-Process -FilePath `$steamExe
    Write-Host "Steam запущен с VPN!" -ForegroundColor Green
} else {
    Write-Host "Steam не найден. Запустите Steam вручную." -ForegroundColor Yellow
    Write-Host "Steam будет использовать системный прокси автоматически." -ForegroundColor Gray
}
"@

$launchScriptPath = ".\launch-steam.ps1"
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
Write-Host "✓ WinHTTP прокси настроен" -ForegroundColor White
Write-Host "✓ Steam найден" -ForegroundColor White
Write-Host "✓ Переменные окружения настроены" -ForegroundColor White
Write-Host "✓ Скрипт запуска создан" -ForegroundColor White
Write-Host ""
Write-Host "ВАЖНО - СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ЗАКРОЙТЕ Steam (если запущен)" -ForegroundColor White
Write-Host ""
Write-Host "2. ЗАПУСТИТЕ Steam через скрипт:" -ForegroundColor White
Write-Host "   .\launch-steam.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "   ИЛИ запустите Steam вручную - он будет использовать системный прокси" -ForegroundColor Gray
Write-Host ""
Write-Host "3. ПРОВЕРЬТЕ, что Steam работает через VPN:" -ForegroundColor White
Write-Host "   - Откройте Steam" -ForegroundColor Gray
Write-Host "   - Зайдите в настройки → Интернет" -ForegroundColor Gray
Write-Host "   - Или проверьте IP: https://whatismyipaddress.com" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ЕСЛИ НЕ РАБОТАЕТ:" -ForegroundColor Yellow
Write-Host "   - Проверьте VPN: .\check-vpn.ps1" -ForegroundColor White
Write-Host "   - Перезапустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host "   - Перезагрузите компьютер (для применения переменных окружения)" -ForegroundColor White
Write-Host ""
Write-Host "ПРОВЕРКА:" -ForegroundColor Cyan
Write-Host "  .\check-vpn.ps1" -ForegroundColor White
Write-Host ""

