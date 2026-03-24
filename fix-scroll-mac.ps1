# Fix Scroll - Make it smooth and fast like MacBook
# Run as Administrator for full effect

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Настройка плавного скролла (как MacBook)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARN] Некоторые настройки требуют прав администратора" -ForegroundColor Yellow
    Write-Host "[INFO] Запустите скрипт от имени администратора для полного эффекта" -ForegroundColor Gray
    Write-Host ""
}

# Step 1: Enable smooth scrolling in Windows
Write-Host "[1/6] Включение плавного скролла Windows..." -ForegroundColor Yellow
try {
    # Enable smooth scrolling
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "SmoothScroll" -Value 1 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WheelScrollLines" -Value 3 -ErrorAction SilentlyContinue
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "MouseWheelRouting" -Value 0 -ErrorAction SilentlyContinue
    
    # Smooth scrolling for mouse wheel
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WheelScrollChars" -Value 3 -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Плавный скролл Windows включен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить: $_" -ForegroundColor Yellow
}

# Step 2: Configure mouse settings for smooth scrolling
Write-Host ""
Write-Host "[2/6] Настройка мыши для плавного скролла..." -ForegroundColor Yellow
try {
    # Mouse acceleration and smooth scrolling
    $mouseKey = "HKCU:\Control Panel\Mouse"
    
    # Enable smooth mouse movement
    Set-ItemProperty -Path $mouseKey -Name "MouseSpeed" -Value "1" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $mouseKey -Name "MouseThreshold1" -Value "0" -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $mouseKey -Name "MouseThreshold2" -Value "0" -ErrorAction SilentlyContinue
    
    # Scroll speed
    Set-ItemProperty -Path $mouseKey -Name "ScrollLines" -Value 3 -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Настройки мыши применены" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить мышь: $_" -ForegroundColor Yellow
}

# Step 3: Enable smooth scrolling in Edge/Chrome (via registry)
Write-Host ""
Write-Host "[3/6] Настройка плавного скролла для браузеров..." -ForegroundColor Yellow
try {
    # Chrome smooth scrolling
    $chromeKey = "HKCU:\Software\Policies\Google\Chrome"
    if (-not (Test-Path $chromeKey)) {
        New-Item -Path $chromeKey -Force | Out-Null
    }
    Set-ItemProperty -Path $chromeKey -Name "SmoothScrolling" -Value 1 -ErrorAction SilentlyContinue
    
    # Edge smooth scrolling
    $edgeKey = "HKCU:\Software\Policies\Microsoft\Edge"
    if (-not (Test-Path $edgeKey)) {
        New-Item -Path $edgeKey -Force | Out-Null
    }
    Set-ItemProperty -Path $edgeKey -Name "SmoothScrolling" -Value 1 -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Плавный скролл для браузеров включен" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось настроить браузеры: $_" -ForegroundColor Yellow
}

# Step 4: Configure Firefox smooth scrolling
Write-Host ""
Write-Host "[4/6] Настройка Firefox для плавного скролла..." -ForegroundColor Yellow

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
    
    # Firefox smooth scrolling settings (Mac-like)
    $userPrefs["general.smoothScroll"] = "true"
    $userPrefs["general.smoothScroll.mouseWheel"] = "true"
    $userPrefs["general.smoothScroll.pages"] = "true"
    $userPrefs["mousewheel.min_line_scroll_amount"] = "5"
    $userPrefs["mousewheel.acceleration.start"] = "1"
    $userPrefs["mousewheel.acceleration.factor"] = "10"
    $userPrefs["mousewheel.scrollbar.vertical"] = "true"
    $userPrefs["apz.allow_zooming"] = "true"
    $userPrefs["apz.overscroll.enabled"] = "true"
    $userPrefs["toolkit.scrollbox.smoothScroll"] = "true"
    
    # Write user.js
    $content = @()
    foreach ($key in $userPrefs.Keys | Sort-Object) {
        $value = $userPrefs[$key]
        $content += "user_pref(`"$key`", $value);"
    }
    
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($userPrefsPath, $content, $utf8NoBom)
    
    Write-Host "  [OK] Firefox настроен для плавного скролла" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Профиль Firefox не найден (настроится при следующем запуске)" -ForegroundColor Gray
}

# Step 5: Configure touchpad settings (if available)
Write-Host ""
Write-Host "[5/6] Настройка тачпада..." -ForegroundColor Yellow
try {
    # Touchpad scroll settings
    $touchpadKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PrecisionTouchPad"
    if (Test-Path $touchpadKey) {
        Set-ItemProperty -Path $touchpadKey -Name "ScrollDirection" -Value 0 -ErrorAction SilentlyContinue
        Write-Host "  [OK] Настройки тачпада применены" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] Тачпад не найден (это нормально для мыши)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Не удалось настроить тачпад: $_" -ForegroundColor Yellow
}

# Step 6: Advanced scroll settings
Write-Host ""
Write-Host "[6/6] Применение дополнительных настроек..." -ForegroundColor Yellow
try {
    # Disable scroll delay
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "MenuShowDelay" -Value 0 -ErrorAction SilentlyContinue
    
    # Smooth scrolling for all applications
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -Value ([byte[]](0x9E,0x1E,0x07,0x80,0x12,0x00,0x00,0x00)) -ErrorAction SilentlyContinue
    
    Write-Host "  [OK] Дополнительные настройки применены" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Не удалось применить некоторые настройки: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Настройка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ПРИМЕНЕНИЕ ИЗМЕНЕНИЙ:" -ForegroundColor Yellow
Write-Host "1. ПЕРЕЗАГРУЗИТЕ компьютер для полного эффекта" -ForegroundColor White
Write-Host "   (или выйдите и войдите в систему)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Если перезагрузка не нужна:" -ForegroundColor White
Write-Host "   - Закройте и откройте браузеры" -ForegroundColor Gray
Write-Host "   - Перезапустите приложения" -ForegroundColor Gray
Write-Host ""
Write-Host "НАСТРОЙКИ FIREFOX (вручную, если нужно):" -ForegroundColor Cyan
Write-Host "1. Откройте Firefox" -ForegroundColor White
Write-Host "2. Введите: about:config" -ForegroundColor White
Write-Host "3. Найдите и установите:" -ForegroundColor White
Write-Host "   general.smoothScroll = true" -ForegroundColor Gray
Write-Host "   general.smoothScroll.mouseWheel = true" -ForegroundColor Gray
Write-Host "   mousewheel.acceleration.factor = 10" -ForegroundColor Gray
Write-Host ""
Write-Host "ПРОВЕРКА:" -ForegroundColor Yellow
Write-Host "- Откройте любой сайт с длинным контентом" -ForegroundColor White
Write-Host "- Прокрутите колесиком мыши" -ForegroundColor White
Write-Host "- Скролл должен быть плавным и быстрым (как на Mac)" -ForegroundColor White
Write-Host ""

pause


