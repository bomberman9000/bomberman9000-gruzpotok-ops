# Check VPN (Hysteria2) Status
# Comprehensive VPN connection check

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Проверка работы VPN (Hysteria2)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Hysteria2 process is running
Write-Host "[1/5] Проверка процесса Hysteria2..." -ForegroundColor Yellow
$hysteriaProcess = Get-Process -Name "hysteria2" -ErrorAction SilentlyContinue
if ($hysteriaProcess) {
    Write-Host "  [OK] Hysteria2 запущен (PID: $($hysteriaProcess.Id))" -ForegroundColor Green
    Write-Host "      Путь: $($hysteriaProcess.Path)" -ForegroundColor Gray
} else {
    Write-Host "  [ERROR] Hysteria2 НЕ запущен!" -ForegroundColor Red
    Write-Host "      Запустите: .\start-hysteria2.ps1" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Check system proxy settings
Write-Host "[2/5] Проверка системного прокси..." -ForegroundColor Yellow
$proxyEnabled = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyEnable" -ErrorAction SilentlyContinue).ProxyEnable
$proxyServer = (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -Name "ProxyServer" -ErrorAction SilentlyContinue).ProxyServer

if ($proxyEnabled -eq 1) {
    Write-Host "  [OK] Системный прокси включен" -ForegroundColor Green
    Write-Host "      Сервер: $proxyServer" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Системный прокси выключен" -ForegroundColor Yellow
    Write-Host "      Включите: .\enable-proxy.ps1" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Check WinHTTP proxy
Write-Host "[3/5] Проверка WinHTTP прокси..." -ForegroundColor Yellow
try {
    $winhttpProxy = netsh winhttp show proxy
    if ($winhttpProxy -match "Прямое подключение") {
        Write-Host "  [WARN] WinHTTP прокси не настроен" -ForegroundColor Yellow
    } else {
        Write-Host "  [OK] WinHTTP прокси настроен" -ForegroundColor Green
        Write-Host "      $($winhttpProxy -replace "`n", " ")" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [INFO] Не удалось проверить WinHTTP" -ForegroundColor Gray
}

Write-Host ""

# Step 4: Test internet connection through proxy
Write-Host "[4/5] Проверка интернет-соединения..." -ForegroundColor Yellow
try {
    # Test basic connectivity
    $ping = Test-Connection -ComputerName "8.8.8.8" -Count 2 -Quiet
    if ($ping) {
        Write-Host "  [OK] Интернет работает" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Нет интернет-соединения" -ForegroundColor Red
    }
} catch {
    Write-Host "  [WARN] Не удалось проверить соединение" -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Check IP address (to verify VPN is working)
Write-Host "[5/5] Проверка IP адреса..." -ForegroundColor Yellow
try {
    Write-Host "  Проверяю внешний IP..." -ForegroundColor Gray
    
    # Try multiple services
    $ipServices = @(
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    )
    
    $ipFound = $false
    foreach ($service in $ipServices) {
        try {
            $ip = Invoke-RestMethod -Uri $service -TimeoutSec 5 -ErrorAction Stop
            if ($ip -match '^\d+\.\d+\.\d+\.\d+$') {
                Write-Host "  [OK] Ваш IP адрес: $ip" -ForegroundColor Green
                Write-Host "      Сервис: $service" -ForegroundColor Gray
                
                # Check if IP is from VPN server region (basic check)
                Write-Host "      Проверка локации..." -ForegroundColor Gray
                try {
                    $geoInfo = Invoke-RestMethod -Uri "http://ip-api.com/json/$ip" -TimeoutSec 5 -ErrorAction Stop
                    if ($geoInfo.status -eq "success") {
                        Write-Host "      Страна: $($geoInfo.country)" -ForegroundColor Cyan
                        Write-Host "      Город: $($geoInfo.city)" -ForegroundColor Cyan
                        Write-Host "      Провайдер: $($geoInfo.isp)" -ForegroundColor Cyan
                    }
                } catch {
                    # Ignore geo check errors
                }
                
                $ipFound = $true
                break
            }
        } catch {
            continue
        }
    }
    
    if (-not $ipFound) {
        Write-Host "  [WARN] Не удалось определить IP адрес" -ForegroundColor Yellow
        Write-Host "      Возможно, VPN блокирует запросы" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [ERROR] Ошибка при проверке IP: $_" -ForegroundColor Red
}

Write-Host ""

# Step 6: Test specific services
Write-Host "[6/6] Проверка доступа к сервисам..." -ForegroundColor Yellow
$testUrls = @(
    @{Name="Google"; Url="https://www.google.com"},
    @{Name="YouTube"; Url="https://www.youtube.com"},
    @{Name="ChatGPT"; Url="https://chat.openai.com"}
)

foreach ($test in $testUrls) {
    try {
        $response = Invoke-WebRequest -Uri $test.Url -Method Head -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($test.Name) доступен" -ForegroundColor Green
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 403 -or $statusCode -eq 451) {
            Write-Host "  [WARN] $($test.Name) заблокирован (код: $statusCode)" -ForegroundColor Yellow
        } else {
            Write-Host "  [ERROR] $($test.Name) недоступен: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "РЕЗУЛЬТАТЫ ПРОВЕРКИ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Summary
$allOk = $true

if (-not $hysteriaProcess) {
    Write-Host "[!] Hysteria2 не запущен" -ForegroundColor Red
    $allOk = $false
}

if ($proxyEnabled -ne 1) {
    Write-Host "[!] Системный прокси выключен" -ForegroundColor Yellow
    $allOk = $false
}

if ($allOk) {
    Write-Host "[✓] VPN работает корректно!" -ForegroundColor Green
} else {
    Write-Host "[!] VPN требует настройки" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "ИСПРАВЛЕНИЕ:" -ForegroundColor Yellow
    Write-Host "1. Запустите VPN: .\start-hysteria2.ps1" -ForegroundColor White
    Write-Host "2. Включите прокси: .\enable-proxy.ps1" -ForegroundColor White
    Write-Host "3. Перезапустите браузеры" -ForegroundColor White
}

Write-Host ""
Write-Host "ДОПОЛНИТЕЛЬНО:" -ForegroundColor Cyan
Write-Host "- Проверьте IP на: https://whatismyipaddress.com" -ForegroundColor White
Write-Host "- Проверьте доступность сайтов в браузере" -ForegroundColor White
Write-Host ""

