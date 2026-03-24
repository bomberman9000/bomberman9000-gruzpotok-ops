# Fix ChatGPT Access - Complete Solution
# This script fixes ChatGPT access through VPN

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Исправление доступа к ChatGPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Hysteria2
Write-Host "[1/7] Проверка Hysteria2..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteria2) {
    Write-Host "  [OK] Hysteria2 работает (PID: $($hysteria2.Id))" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Hysteria2 НЕ запущен!" -ForegroundColor Red
    Write-Host "  [INFO] Запускаю Hysteria2..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  [ERROR] Не найден start-hysteria2.ps1" -ForegroundColor Red
        Write-Host "  [INFO] Запустите Hysteria2 вручную" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 2: Ensure proxy is enabled
Write-Host "[2/7] Проверка системного прокси..." -ForegroundColor Yellow
$proxyEnabled = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable
if ($proxyEnabled -ne 1) {
    Write-Host "  [WARN] Системный прокси выключен, включаю..." -ForegroundColor Yellow
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyEnable" -Value 1
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyServer" -Value "127.0.0.1:8080"
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
} else {
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
}

Write-Host ""

# Step 3: Configure WinHTTP proxy
Write-Host "[3/7] Настройка WinHTTP прокси..." -ForegroundColor Yellow
try {
    netsh winhttp set proxy proxy-server="127.0.0.1:8080" bypass-list="" | Out-Null
    Write-Host "  [OK] WinHTTP прокси настроен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить WinHTTP: $_" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Configure Firefox proxy (remove ChatGPT from bypass)
Write-Host "[4/7] Настройка Firefox для ChatGPT..." -ForegroundColor Yellow

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

if ($profilePath) {
    $prefsPath = Join-Path $profilePath "prefs.js"
    $userPrefsPath = Join-Path $profilePath "user.js"
    
    # Read existing prefs
    $prefs = @{}
    if (Test-Path $prefsPath) {
        Get-Content $prefsPath -Encoding UTF8 | ForEach-Object {
            if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
                $prefs[$matches[1]] = $matches[2]
            }
        }
    }
    
    # Read user.js if exists
    if (Test-Path $userPrefsPath) {
        Get-Content $userPrefsPath -Encoding UTF8 | ForEach-Object {
            if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
                $prefs[$matches[1]] = $matches[2]
            }
        }
    }
    
    # Configure proxy for ChatGPT (force through VPN)
    $prefs["network.proxy.type"] = "1"  # Manual proxy
    $prefs["network.proxy.http"] = "127.0.0.1"
    $prefs["network.proxy.http_port"] = "8080"
    $prefs["network.proxy.ssl"] = "127.0.0.1"
    $prefs["network.proxy.ssl_port"] = "8080"
    $prefs["network.proxy.socks"] = "127.0.0.1"
    $prefs["network.proxy.socks_port"] = "1080"
    $prefs["network.proxy.socks_version"] = "5"
    $prefs["network.proxy.socks_remote_dns"] = "true"
    
    # Get current bypass list
    $bypassList = ""
    if ($prefs.ContainsKey("network.proxy.no_proxies_on")) {
        $bypassList = $prefs["network.proxy.no_proxies_on"]
        # Remove ChatGPT domains from bypass
        $bypassList = $bypassList -replace ',\s*chat\.openai\.com', ''
        $bypassList = $bypassList -replace 'chat\.openai\.com\s*,?\s*', ''
        $bypassList = $bypassList -replace ',\s*openai\.com', ''
        $bypassList = $bypassList -replace 'openai\.com\s*,?\s*', ''
        $bypassList = $bypassList -replace ',\s*api\.openai\.com', ''
        $bypassList = $bypassList -replace 'api\.openai\.com\s*,?\s*', ''
    }
    
    # Set bypass (localhost and local network only)
    if ([string]::IsNullOrWhiteSpace($bypassList)) {
        $prefs["network.proxy.no_proxies_on"] = '"localhost, 127.0.0.1, ::1"'
    } else {
        $prefs["network.proxy.no_proxies_on"] = "`"$bypassList`""
    }
    
    # Write user.js
    $content = @()
    foreach ($key in $prefs.Keys | Sort-Object) {
        $value = $prefs[$key]
        $content += "user_pref(`"$key`", $value);"
    }
    
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($userPrefsPath, $content, $utf8NoBom)
    
    Write-Host "  [OK] Firefox настроен (ChatGPT через VPN)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Профиль Firefox не найден" -ForegroundColor Yellow
    Write-Host "  [INFO] Настройте Firefox вручную (см. инструкции)" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Clear DNS cache
Write-Host "[5/7] Очистка DNS кэша..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    Write-Host "  [OK] DNS кэш очищен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось очистить DNS: $_" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Test ChatGPT connection
Write-Host "[6/7] Проверка доступа к ChatGPT..." -ForegroundColor Yellow
try {
    $chatgptUrl = "https://chat.openai.com"
    $response = Invoke-WebRequest -Uri $chatgptUrl -Method Head -TimeoutSec 10 -UseBasicParsing -Proxy "http://127.0.0.1:8080" -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] ChatGPT доступен (код: 200)" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] ChatGPT ответил с кодом: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 403) {
        Write-Host "  [WARN] ChatGPT заблокирован (403) - возможно, детектирует VPN" -ForegroundColor Yellow
        Write-Host "  [INFO] Попробуйте очистить cookies в браузере" -ForegroundColor Gray
    } elseif ($statusCode -eq 429) {
        Write-Host "  [WARN] Слишком много запросов (429) - подождите" -ForegroundColor Yellow
    } else {
        Write-Host "  [WARN] Ошибка доступа: $_" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 7: Check IP address
Write-Host "[7/7] Проверка IP адреса..." -ForegroundColor Yellow
try {
    $ip = Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 5 -Proxy "http://127.0.0.1:8080" -ErrorAction Stop
    Write-Host "  [OK] Ваш IP через VPN: $ip" -ForegroundColor Green
    
    # Check location
    try {
        $geoInfo = Invoke-RestMethod -Uri "http://ip-api.com/json/$ip" -TimeoutSec 5 -ErrorAction Stop
        if ($geoInfo.status -eq "success") {
            Write-Host "  [INFO] Страна: $($geoInfo.country)" -ForegroundColor Cyan
            Write-Host "  [INFO] Город: $($geoInfo.city)" -ForegroundColor Cyan
        }
    } catch {
        # Ignore geo check errors
    }
} catch {
    Write-Host "  [WARN] Не удалось определить IP: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Настройка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ВАЖНО - СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ЗАКРОЙТЕ Firefox полностью" -ForegroundColor White
Write-Host "   - Закройте все окна Firefox" -ForegroundColor Gray
Write-Host "   - Проверьте диспетчер задач (нет процессов firefox.exe)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. ОТКРОЙТЕ Firefox снова" -ForegroundColor White
Write-Host ""
Write-Host "3. ОЧИСТИТЕ cookies и кэш для ChatGPT:" -ForegroundColor White
Write-Host "   - Нажмите Ctrl+Shift+Delete" -ForegroundColor Gray
Write-Host "   - Выберите 'Cookies' и 'Кэш'" -ForegroundColor Gray
Write-Host "   - Временной диапазон: 'Все'" -ForegroundColor Gray
Write-Host "   - Или только для openai.com" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ОТКРОЙТЕ ChatGPT:" -ForegroundColor White
Write-Host "   - https://chat.openai.com" -ForegroundColor Cyan
Write-Host "   - Или в режиме инкогнито (Ctrl+Shift+P)" -ForegroundColor Gray
Write-Host ""
Write-Host "5. ЕСЛИ НЕ РАБОТАЕТ:" -ForegroundColor Yellow
Write-Host "   - Попробуйте другой браузер (Chrome/Edge)" -ForegroundColor White
Write-Host "   - Проверьте, что VPN работает: .\check-vpn.ps1" -ForegroundColor White
Write-Host "   - Перезапустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host ""
Write-Host "ПРОВЕРКА VPN:" -ForegroundColor Cyan
Write-Host "  .\check-vpn.ps1" -ForegroundColor White
Write-Host ""

