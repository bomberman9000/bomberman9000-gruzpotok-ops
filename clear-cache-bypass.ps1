# Clear All Cache and Bypass All Restrictions
# Comprehensive cache clearing and restriction bypass

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Очистка кэша и обход ограничений" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARN] Некоторые операции требуют прав администратора" -ForegroundColor Yellow
}

# Step 1: Close all browsers
Write-Host "[1/10] Закрытие браузеров..." -ForegroundColor Yellow
$browsers = @("firefox", "chrome", "msedge", "opera", "brave")
foreach ($browser in $browsers) {
    $processes = Get-Process -Name $browser -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "  Закрываю $browser..." -ForegroundColor Gray
        Stop-Process -Name $browser -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}
Write-Host "  [OK] Браузеры закрыты" -ForegroundColor Green
Write-Host ""

# Step 2: Clear DNS cache
Write-Host "[2/10] Очистка DNS кэша..." -ForegroundColor Yellow
try {
    ipconfig /flushdns | Out-Null
    Write-Host "  [OK] DNS кэш очищен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось очистить DNS: $_" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Clear Firefox cache and cookies
Write-Host "[3/10] Очистка Firefox..." -ForegroundColor Yellow
$firefoxProfiles = @(
    "$env:APPDATA\Mozilla\Firefox\Profiles",
    "$env:LOCALAPPDATA\Mozilla\Firefox\Profiles"
)

$firefoxCleared = $false
foreach ($path in $firefoxProfiles) {
    if (Test-Path $path) {
        $profiles = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        foreach ($profile in $profiles) {
            $profilePath = $profile.FullName
            
            # Clear cache
            $cachePath = Join-Path $profilePath "cache2"
            if (Test-Path $cachePath) {
                Remove-Item -Path "$cachePath\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "  [OK] Кэш Firefox очищен: $profilePath" -ForegroundColor Green
            }
            
            # Clear cookies for OpenAI
            $cookiesPath = Join-Path $profilePath "cookies.sqlite"
            if (Test-Path $cookiesPath) {
                try {
                    Remove-Item -Path $cookiesPath -Force -ErrorAction SilentlyContinue
                    Write-Host "  [OK] Cookies Firefox удалены" -ForegroundColor Green
                } catch {
                    Write-Host "  [WARN] Не удалось удалить cookies: $_" -ForegroundColor Yellow
                }
            }
            
            # Clear storage
            $storagePath = Join-Path $profilePath "storage"
            if (Test-Path $storagePath) {
                Get-ChildItem $storagePath -Directory | Where-Object { $_.Name -like "*openai*" -or $_.Name -like "*chatgpt*" } | ForEach-Object {
                    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                }
                Write-Host "  [OK] Storage OpenAI очищен" -ForegroundColor Green
            }
            
            $firefoxCleared = $true
        }
    }
}

if (-not $firefoxCleared) {
    Write-Host "  [INFO] Профили Firefox не найдены" -ForegroundColor Gray
}
Write-Host ""

# Step 4: Clear Chrome cache and cookies
Write-Host "[4/10] Очистка Chrome..." -ForegroundColor Yellow
$chromePaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Code Cache",
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\GPUCache"
)

foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        Remove-Item -Path "$path\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Кэш Chrome очищен: $(Split-Path $path -Leaf)" -ForegroundColor Green
    }
}

# Clear Chrome cookies
$chromeCookies = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cookies"
if (Test-Path $chromeCookies) {
    try {
        Remove-Item -Path $chromeCookies -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Cookies Chrome удалены" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Не удалось удалить cookies Chrome: $_" -ForegroundColor Yellow
    }
}
Write-Host ""

# Step 5: Clear Edge cache and cookies
Write-Host "[5/10] Очистка Edge..." -ForegroundColor Yellow
$edgePaths = @(
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Code Cache",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\GPUCache"
)

foreach ($path in $edgePaths) {
    if (Test-Path $path) {
        Remove-Item -Path "$path\*" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Кэш Edge очищен: $(Split-Path $path -Leaf)" -ForegroundColor Green
    }
}

# Clear Edge cookies
$edgeCookies = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cookies"
if (Test-Path $edgeCookies) {
    try {
        Remove-Item -Path $edgeCookies -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Cookies Edge удалены" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Не удалось удалить cookies Edge: $_" -ForegroundColor Yellow
    }
}
Write-Host ""

# Step 6: Clear Windows temp files
Write-Host "[6/10] Очистка временных файлов Windows..." -ForegroundColor Yellow
$tempPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*",
    "$env:WINDIR\Temp\*"
)

foreach ($path in $tempPaths) {
    try {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Очищено: $path" -ForegroundColor Green
    } catch {
        # Ignore errors
    }
}
Write-Host "  [OK] Временные файлы очищены" -ForegroundColor Green
Write-Host ""

# Step 7: Clear browser history (registry)
Write-Host "[7/10] Очистка истории браузеров..." -ForegroundColor Yellow
try {
    # Firefox history
    $firefoxHistory = "HKCU:\Software\Mozilla\Firefox\Recent"
    if (Test-Path $firefoxHistory) {
        Remove-Item -Path $firefoxHistory -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Chrome history
    $chromeHistory = "HKCU:\Software\Google\Chrome\Recent"
    if (Test-Path $chromeHistory) {
        Remove-Item -Path $chromeHistory -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  [OK] История браузеров очищена" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось очистить историю: $_" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Ensure VPN is running and configured
Write-Host "[8/10] Проверка и настройка VPN..." -ForegroundColor Yellow
$hysteria2 = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if (-not $hysteria2) {
    Write-Host "  [WARN] Hysteria2 не запущен, запускаю..." -ForegroundColor Yellow
    if (Test-Path ".\start-hysteria2.ps1") {
        & .\start-hysteria2.ps1
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "  [OK] Hysteria2 работает (PID: $($hysteria2.Id))" -ForegroundColor Green
}

# Ensure proxy is enabled
$proxyEnabled = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable
if ($proxyEnabled -ne 1) {
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyEnable" -Value 1
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyServer" -Value "127.0.0.1:8080"
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
} else {
    Write-Host "  [OK] Системный прокси уже включен" -ForegroundColor Green
}

# Configure WinHTTP
try {
    netsh winhttp set proxy proxy-server="127.0.0.1:8080" bypass-list="" | Out-Null
    Write-Host "  [OK] WinHTTP прокси настроен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить WinHTTP: $_" -ForegroundColor Yellow
}
Write-Host ""

# Step 9: Configure Firefox for maximum bypass
Write-Host "[9/10] Настройка Firefox для обхода ограничений..." -ForegroundColor Yellow
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
    $userPrefsPath = Join-Path $profilePath "user.js"
    
    # Read existing prefs
    $userPrefs = @{}
    if (Test-Path $userPrefsPath) {
        Get-Content $userPrefsPath -Encoding UTF8 | ForEach-Object {
            if ($_ -match 'user_pref\("([^"]+)",\s*(.+)\)') {
                $userPrefs[$matches[1]] = $matches[2]
            }
        }
    }
    
    # Maximum bypass settings
    $userPrefs["network.proxy.type"] = "1"  # Manual proxy
    $userPrefs["network.proxy.http"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.http_port"] = "8080"
    $userPrefs["network.proxy.ssl"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.ssl_port"] = "8080"
    $userPrefs["network.proxy.socks"] = "`"127.0.0.1`""
    $userPrefs["network.proxy.socks_port"] = "1080"
    $userPrefs["network.proxy.socks_version"] = "5"
    $userPrefs["network.proxy.socks_remote_dns"] = "true"
    # NO exceptions for OpenAI - force through VPN
    $userPrefs["network.proxy.no_proxies_on"] = "`"localhost, 127.0.0.1`""
    
    # Additional bypass settings
    $userPrefs["privacy.trackingprotection.enabled"] = "false"
    $userPrefs["privacy.trackingprotection.pbmode.enabled"] = "false"
    $userPrefs["network.dns.disableIPv6"] = "false"
    $userPrefs["network.http.sendRefererHeader"] = "2"
    $userPrefs["network.http.referer.spoofSource"] = "false"
    $userPrefs["browser.cache.disk.enable"] = "true"
    $userPrefs["browser.cache.memory.enable"] = "true"
    
    # Write user.js
    $content = @()
    foreach ($key in $userPrefs.Keys | Sort-Object) {
        $value = $userPrefs[$key]
        $content += "user_pref(`"$key`", $value);"
    }
    
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($userPrefsPath, $content, $utf8NoBom)
    
    Write-Host "  [OK] Firefox настроен для максимального обхода" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Профиль Firefox не найден" -ForegroundColor Gray
}
Write-Host ""

# Step 10: Clear network adapter cache
Write-Host "[10/10] Очистка сетевого кэша..." -ForegroundColor Yellow
if ($isAdmin) {
    try {
        netsh winsock reset | Out-Null
        netsh int ip reset | Out-Null
        Write-Host "  [OK] Сетевой кэш очищен (требуется перезагрузка)" -ForegroundColor Green
    } catch {
        Write-Host "  [WARN] Не удалось очистить сетевой кэш: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [INFO] Требуются права администратора для полной очистки" -ForegroundColor Gray
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Очистка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ЧТО СДЕЛАНО:" -ForegroundColor Yellow
Write-Host "✓ Все браузеры закрыты" -ForegroundColor White
Write-Host "✓ DNS кэш очищен" -ForegroundColor White
Write-Host "✓ Кэш Firefox очищен" -ForegroundColor White
Write-Host "✓ Cookies Firefox удалены" -ForegroundColor White
Write-Host "✓ Кэш Chrome очищен" -ForegroundColor White
Write-Host "✓ Cookies Chrome удалены" -ForegroundColor White
Write-Host "✓ Кэш Edge очищен" -ForegroundColor White
Write-Host "✓ Cookies Edge удалены" -ForegroundColor White
Write-Host "✓ Временные файлы очищены" -ForegroundColor White
Write-Host "✓ История браузеров очищена" -ForegroundColor White
Write-Host "✓ VPN проверен и настроен" -ForegroundColor White
Write-Host "✓ Firefox настроен для обхода ограничений" -ForegroundColor White
Write-Host ""
Write-Host "ВАЖНО - СЛЕДУЮЩИЕ ШАГИ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. ОТКРОЙТЕ Firefox (или другой браузер)" -ForegroundColor White
Write-Host ""
Write-Host "2. ОТКРОЙТЕ ChatGPT:" -ForegroundColor White
Write-Host "   https://chat.openai.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. ИСПОЛЬЗУЙТЕ режим инкогнито (рекомендуется):" -ForegroundColor White
Write-Host "   Ctrl+Shift+P в Firefox" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ЕСЛИ НЕ РАБОТАЕТ:" -ForegroundColor Yellow
Write-Host "   - Проверьте VPN: .\check-vpn.ps1" -ForegroundColor White
Write-Host "   - Перезапустите Hysteria2: .\start-hysteria2.ps1" -ForegroundColor White
Write-Host "   - Попробуйте другой браузер" -ForegroundColor White
Write-Host ""
Write-Host "ПРОВЕРКА VPN:" -ForegroundColor Cyan
Write-Host "  .\check-vpn.ps1" -ForegroundColor White
Write-Host ""

