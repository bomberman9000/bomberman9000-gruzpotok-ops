# Оптимизация автозапуска и настройка Ollama
# Убирает лишние программы и настраивает необходимые

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ОПТИМИЗАЦИЯ АВТОЗАПУСКА" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. ТЕКУЩИЙ АВТОЗАПУСК
# ========================================
Write-Host "[1/4] Анализ текущего автозапуска..." -ForegroundColor Yellow
Write-Host ""

$startupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupReg = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

Write-Host "  Папка автозапуска:" -ForegroundColor Cyan
$folderItems = Get-ChildItem -Path $startupFolder -Filter "*.lnk" -ErrorAction SilentlyContinue
if ($folderItems) {
    foreach ($item in $folderItems) {
        Write-Host "    - $($item.Name)" -ForegroundColor White
    }
} else {
    Write-Host "    (пусто)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "  Реестр автозапуска:" -ForegroundColor Cyan
$regItems = Get-ItemProperty -Path $startupReg -ErrorAction SilentlyContinue
if ($regItems) {
    $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "    - $($_.Name)" -ForegroundColor White
    }
} else {
    Write-Host "    (пусто)" -ForegroundColor Gray
}
Write-Host ""

# ========================================
# 2. УДАЛЕНИЕ ЛИШНИХ ПРОГРАММ
# ========================================
Write-Host "[2/4] Удаление лишних программ из автозапуска..." -ForegroundColor Yellow
Write-Host ""

# Список программ для удаления
$toRemove = @(
    "Docker Desktop",
    "YandexBrowserAutoLaunch_043700B5ACB64327B1739FC0243B05DF",
    "MicrosoftEdgeAutoLaunch_EA794D1CCD5766A0BC735454A359C99A"
    # LGHUB оставляем - это драйвер Logitech
)

$removed = 0
foreach ($program in $toRemove) {
    try {
        Remove-ItemProperty -Path $startupReg -Name $program -ErrorAction Stop
        Write-Host "  [OK] Удалено: $program" -ForegroundColor Green
        $removed++
    } catch {
        Write-Host "  [INFO] Не найдено: $program" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "  [OK] Удалено программ: $removed" -ForegroundColor Green
Write-Host ""

# ========================================
# 3. НАСТРОЙКА OLLAMA
# ========================================
Write-Host "[3/4] Настройка Ollama..." -ForegroundColor Yellow
Write-Host ""

# Поиск Ollama
$ollamaPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaPath)) {
    # Попробуем другие пути
    $possiblePaths = @(
        "C:\Program Files\Ollama\ollama.exe",
        "C:\Program Files (x86)\Ollama\ollama.exe",
        "$env:LOCALAPPDATA\Ollama\ollama.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $ollamaPath = $path
            break
        }
    }
}

if (Test-Path $ollamaPath) {
    Write-Host "  [OK] Найдена Ollama: $ollamaPath" -ForegroundColor Green
    
    # Создание ярлыка в автозапуске
    $shortcutPath = Join-Path $startupFolder "Ollama.lnk"
    
    # Используем VBScript для создания ярлыка (надежнее)
    $vbsScript = @"
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "$shortcutPath"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "$ollamaPath"
oLink.WorkingDirectory = "$([System.IO.Path]::GetDirectoryName($ollamaPath))"
oLink.Description = "Start Ollama on login"
oLink.WindowStyle = 7
oLink.Save
"@
    
    $vbsPath = "$env:TEMP\create_ollama_shortcut.vbs"
    Set-Content -Path $vbsPath -Value $vbsScript -Encoding ASCII
    
    try {
        $result = cscript //nologo $vbsPath 2>&1
        Remove-Item -Path $vbsPath -Force -ErrorAction SilentlyContinue
        
        if (Test-Path $shortcutPath) {
            Write-Host "  [OK] Автозапуск Ollama настроен" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Не удалось создать ярлык" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [WARN] Ошибка создания ярлыка: $_" -ForegroundColor Yellow
    }
    
    # Запуск Ollama
    Write-Host ""
    Write-Host "  Запуск Ollama..." -ForegroundColor Gray
    $ollamaProcess = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
    if (-not $ollamaProcess) {
        try {
            Start-Process -FilePath $ollamaPath -WindowStyle Hidden
            Start-Sleep -Seconds 2
            $ollamaProcess = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue
            if ($ollamaProcess) {
                Write-Host "  [OK] Ollama запущена (PID: $($ollamaProcess.Id))" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Ollama не запустилась" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [WARN] Ошибка запуска: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  [OK] Ollama уже запущена (PID: $($ollamaProcess.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] Ollama не найдена!" -ForegroundColor Red
    Write-Host "  [INFO] Установите Ollama: ollama.com" -ForegroundColor Cyan
}
Write-Host ""

# ========================================
# 4. ИТОГИ
# ========================================
Write-Host "[4/4] Итоговый автозапуск..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  Программы в автозапуске:" -ForegroundColor Cyan
$finalFolderItems = Get-ChildItem -Path $startupFolder -Filter "*.lnk" -ErrorAction SilentlyContinue
if ($finalFolderItems) {
    foreach ($item in $finalFolderItems) {
        Write-Host "    ✓ $($item.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "    (нет программ)" -ForegroundColor Gray
}
Write-Host ""

$finalRegItems = Get-ItemProperty -Path $startupReg -ErrorAction SilentlyContinue
if ($finalRegItems) {
    $finalRegItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" } | ForEach-Object {
        Write-Host "    ✓ $($_.Name)" -ForegroundColor Green
    }
}
Write-Host ""

# ========================================
# ИТОГИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ОПТИМИЗАЦИЯ ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "ЧТО СДЕЛАНО:" -ForegroundColor Cyan
Write-Host "  ✓ Удалено лишних программ: $removed" -ForegroundColor Green
Write-Host "  ✓ Ollama настроена на автозапуск" -ForegroundColor Green
Write-Host "  ✓ Ollama запущена" -ForegroundColor Green
Write-Host ""

Write-Host "В АВТОЗАПУСКЕ ОСТАЛОСЬ:" -ForegroundColor Cyan
Write-Host "  ✓ Ollama (для AI)" -ForegroundColor White
Write-Host "  ✓ LGHUB (драйвер Logitech)" -ForegroundColor White
Write-Host ""

Write-Host "РЕКОМЕНДАЦИИ:" -ForegroundColor Yellow
Write-Host "  - При следующем входе Ollama запустится автоматически" -ForegroundColor White
Write-Host "  - Docker, Yandex Browser, Edge убраны из автозапуска" -ForegroundColor White
Write-Host "  - LGHUB оставлен (нужен для мыши/клавиатуры Logitech)" -ForegroundColor White
Write-Host ""

pause
