# Setup Firefox Proxy for Hysteria2
# This script automatically configures Firefox proxy settings

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Настройка Firefox для Hysteria2" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Hysteria2 proxy settings
$proxyHost = "127.0.0.1"
$proxyPort = "8080"
$socksPort = "1080"

# Check Hysteria2
Write-Host "[1/5] Проверка Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  [OK] Hysteria2 работает (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Hysteria2 НЕ запущен!" -ForegroundColor Yellow
    Write-Host "  [INFO] Запускаю Hysteria2..." -ForegroundColor Gray
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Не найден start-hysteria2.ps1" -ForegroundColor Red
        Write-Host "  [INFO] Запустите Hysteria2 вручную" -ForegroundColor Yellow
    }
}

# Check proxy ports
Write-Host ""
Write-Host "[2/5] Проверка портов прокси..." -ForegroundColor Yellow
$port8080 = Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue
$port1080 = Get-NetTCPConnection -LocalPort 1080 -State Listen -ErrorAction SilentlyContinue

if ($port8080) {
    Write-Host "  [OK] HTTP прокси порт 8080 активен" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Порт 8080 НЕ активен!" -ForegroundColor Yellow
}

if ($port1080) {
    Write-Host "  [OK] SOCKS5 прокси порт 1080 активен" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Порт 1080 НЕ активен!" -ForegroundColor Yellow
}

# Find Firefox profile
Write-Host ""
Write-Host "[3/5] Поиск профиля Firefox..." -ForegroundColor Yellow

$firefoxProfiles = @(
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"
)

$profilePath = $null
foreach ($path in $firefoxProfiles) {
    if (Test-Path $path) {
        $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        if ($profiles) {
            # Try to find default profile
            $defaultProfile = $profiles | Where-Object { $_.Name -match "default" } | Select-Object -First 1
            if (-not $defaultProfile) {
                # Use the first profile
                $defaultProfile = $profiles | Select-Object -First 1
            }
            $profilePath = $defaultProfile.FullName
            break
        }
    }
}

if (-not $profilePath) {
    Write-Host "  [ERROR] Профиль Firefox не найден!" -ForegroundColor Red
    Write-Host "  [INFO] Запустите Firefox хотя бы один раз для создания профиля" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Нажмите любую клавишу после запуска Firefox..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    # Try again
    foreach ($path in $firefoxProfiles) {
        if (Test-Path $path) {
            $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
            if ($profiles) {
                $defaultProfile = $profiles | Select-Object -First 1
                $profilePath = $defaultProfile.FullName
                break
            }
        }
    }
    
    if (-not $profilePath) {
        Write-Host "  [ERROR] Профиль все еще не найден!" -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host "  [OK] Найден профиль: $profilePath" -ForegroundColor Green

# Configure proxy
Write-Host ""
Write-Host "[4/5] Настройка прокси..." -ForegroundColor Yellow

$userPrefsPath = Join-Path $profilePath "user.js"

# Read existing user.js
$userPrefs = @{}
if (Test-Path $userPrefsPath) {
    Get-Content $userPrefsPath -Encoding UTF8 | ForEach-Object {
        if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
            $userPrefs[$matches[1]] = $matches[2]
        }
    }
}

# Set proxy preferences
$userPrefs["network.proxy.type"] = "1"  # Manual proxy
$userPrefs["network.proxy.http"] = "`"$proxyHost`""
$userPrefs["network.proxy.http_port"] = "$proxyPort"
$userPrefs["network.proxy.ssl"] = "`"$proxyHost`""
$userPrefs["network.proxy.ssl_port"] = "$proxyPort"
$userPrefs["network.proxy.socks"] = "`"$proxyHost`""
$userPrefs["network.proxy.socks_port"] = "$socksPort"
$userPrefs["network.proxy.socks_version"] = "5"
$userPrefs["network.proxy.socks_remote_dns"] = "true"
# Add exceptions for ChatGPT and local addresses
$userPrefs["network.proxy.no_proxies_on"] = "`"localhost, 127.0.0.1, *.openai.com, *.chatgpt.com, *.anthropic.com`""

# Write user.js
$content = @()
foreach ($key in $userPrefs.Keys | Sort-Object) {
    $value = $userPrefs[$key]
    $content += "user_pref(`"$key`", $value);"
}

# Save with UTF-8 encoding
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($userPrefsPath, $content, $utf8NoBom)

Write-Host "  [OK] Настройки прокси сохранены!" -ForegroundColor Green

# Check if Firefox is running
Write-Host ""
Write-Host "[5/5] Проверка Firefox..." -ForegroundColor Yellow
$firefoxProcess = Get-Process -Name "firefox" -ErrorAction SilentlyContinue
if ($firefoxProcess) {
    Write-Host "  [INFO] Firefox запущен (PID: $($firefoxProcess.Id))" -ForegroundColor Gray
    Write-Host "  [WARN] Нужно перезапустить Firefox для применения настроек!" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] Firefox не запущен - настройки применятся при следующем запуске" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Настройка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "НАСТРОЙКИ ПРОКСИ:" -ForegroundColor Cyan
Write-Host "  Тип: Ручная настройка" -ForegroundColor White
Write-Host "  HTTP прокси: $proxyHost`:$proxyPort" -ForegroundColor White
Write-Host "  SSL прокси: $proxyHost`:$proxyPort" -ForegroundColor White
Write-Host "  SOCKS5 прокси: $proxyHost`:$socksPort" -ForegroundColor White
Write-Host "  Исключения: localhost, *.openai.com, *.chatgpt.com" -ForegroundColor White
Write-Host ""
Write-Host "СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host "1. Если Firefox запущен - ЗАКРОЙТЕ его полностью" -ForegroundColor White
Write-Host "2. Запустите Firefox снова" -ForegroundColor White
Write-Host "3. Проверьте настройки:" -ForegroundColor White
Write-Host "   - Меню (☰) → Настройки → Сетевые параметры → Параметры..." -ForegroundColor Gray
Write-Host "   - Должно быть: Ручная настройка прокси" -ForegroundColor Gray
Write-Host "4. Проверьте работу:" -ForegroundColor White
Write-Host "   - Откройте: https://whatismyipaddress.com" -ForegroundColor Gray
Write-Host "   - Должен показаться IP вашего VPN" -ForegroundColor Gray
Write-Host "   - Откройте: https://chat.openai.com" -ForegroundColor Gray
Write-Host "   - ChatGPT должен работать (без прокси)" -ForegroundColor Gray
Write-Host ""

pause


