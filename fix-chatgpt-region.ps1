# Fix ChatGPT Region Block
# Remove ChatGPT from proxy exceptions so it works through VPN

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Исправление блокировки региона ChatGPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INFO] ChatGPT блокирует ваш регион" -ForegroundColor Yellow
Write-Host "[INFO] Нужно использовать VPN/прокси для доступа" -ForegroundColor Yellow
Write-Host ""

# Check Hysteria2
Write-Host "[1/4] Проверка Hysteria2..." -ForegroundColor Yellow
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
        Write-Host "  [INFO] Запустите: .\start-hysteria2.ps1" -ForegroundColor Yellow
    }
}

# Check proxy ports
Write-Host ""
Write-Host "[2/4] Проверка портов прокси..." -ForegroundColor Yellow
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
    Write-Host "  [ERROR] Порт 1080 НЕ активен!" -ForegroundColor Red
}

# Find Firefox profile
Write-Host ""
Write-Host "[3/4] Настройка Firefox..." -ForegroundColor Yellow

$firefoxProfiles = @(
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"
)

$profilePath = $null
foreach ($path in $firefoxProfiles) {
    if (Test-Path $path) {
        $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        if ($profiles) {
            $defaultProfile = $profiles | Where-Object { $_.Name -match "default" } | Select-Object -First 1
            if (-not $defaultProfile) {
                $defaultProfile = $profiles | Select-Object -First 1
            }
            $profilePath = $defaultProfile.FullName
            break
        }
    }
}

if (-not $profilePath) {
    Write-Host "  [ERROR] Профиль Firefox не найден!" -ForegroundColor Red
    Write-Host "  [INFO] Запустите Firefox хотя бы один раз" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "  [OK] Найден профиль: $profilePath" -ForegroundColor Green

# Configure proxy WITHOUT ChatGPT exceptions
Write-Host ""
Write-Host "[4/4] Удаление исключений для ChatGPT..." -ForegroundColor Yellow

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

# Set proxy preferences (WITHOUT ChatGPT exceptions)
$userPrefs["network.proxy.type"] = "1"  # Manual proxy
$userPrefs["network.proxy.http"] = "`"127.0.0.1`""
$userPrefs["network.proxy.http_port"] = "8080"
$userPrefs["network.proxy.ssl"] = "`"127.0.0.1`""
$userPrefs["network.proxy.ssl_port"] = "8080"
$userPrefs["network.proxy.socks"] = "`"127.0.0.1`""
$userPrefs["network.proxy.socks_port"] = "1080"
$userPrefs["network.proxy.socks_version"] = "5"
$userPrefs["network.proxy.socks_remote_dns"] = "true"
# Only localhost exceptions (NO ChatGPT exceptions!)
$userPrefs["network.proxy.no_proxies_on"] = "`"localhost, 127.0.0.1`""

# Write user.js
$content = @()
foreach ($key in $userPrefs.Keys | Sort-Object) {
    $value = $userPrefs[$key]
    $content += "user_pref(`"$key`", $value);"
}

# Save with UTF-8 encoding
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllLines($userPrefsPath, $content, $utf8NoBom)

Write-Host "  [OK] Исключения для ChatGPT удалены!" -ForegroundColor Green
Write-Host "  [OK] ChatGPT теперь будет работать ЧЕРЕЗ прокси" -ForegroundColor Green

# Check if Firefox is running
$firefoxProcess = Get-Process -Name "firefox" -ErrorAction SilentlyContinue
if ($firefoxProcess) {
    Write-Host ""
    Write-Host "  [WARN] Firefox запущен - нужно перезапустить!" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Настройка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ВАЖНО:" -ForegroundColor Yellow
Write-Host "ChatGPT теперь будет работать ЧЕРЕЗ VPN/прокси" -ForegroundColor White
Write-Host "Это обойдет блокировку региона" -ForegroundColor White
Write-Host ""
Write-Host "СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Cyan
Write-Host "1. ЗАКРОЙТЕ Firefox полностью (все окна)" -ForegroundColor White
Write-Host "2. Убедитесь, что Hysteria2 работает:" -ForegroundColor White
Write-Host "   Get-Process -Name `"hysteria2`"" -ForegroundColor Gray
Write-Host "3. Запустите Firefox снова" -ForegroundColor White
Write-Host "4. Откройте: https://chat.openai.com" -ForegroundColor White
Write-Host "5. ChatGPT должен работать через VPN!" -ForegroundColor White
Write-Host ""
Write-Host "ПРОВЕРКА:" -ForegroundColor Cyan
Write-Host "- Откройте: https://whatismyipaddress.com" -ForegroundColor White
Write-Host "- Должен показаться IP вашего VPN (не ваш реальный IP)" -ForegroundColor Gray
Write-Host "- Это означает, что прокси работает" -ForegroundColor Gray
Write-Host ""

pause


