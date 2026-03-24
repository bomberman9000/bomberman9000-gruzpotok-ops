# Установка необходимых программ для Windows 11
# Использует winget (встроенный менеджер пакетов Windows 11)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  УСТАНОВКА НЕОБХОДИМЫХ ПРОГРАММ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка winget
Write-Host "[INFO] Проверка winget..." -ForegroundColor Yellow
$wingetPath = Get-Command winget -ErrorAction SilentlyContinue

if (-not $wingetPath) {
    Write-Host "  [ERROR] winget не найден!" -ForegroundColor Red
    Write-Host "  [INFO] Установите App Installer из Microsoft Store" -ForegroundColor Yellow
    Write-Host "  [INFO] Или обновите Windows 11" -ForegroundColor Yellow
    pause
    exit
}

Write-Host "  [OK] winget обнаружен`n" -ForegroundColor Green

# ========================================
# СПИСОК ПРОГРАММ
# ========================================

$essentialPrograms = @(
    @{
        Name = "7-Zip"
        Id = "7zip.7zip"
        Description = "Архиватор (лучше WinRAR)"
    },
    @{
        Name = "Google Chrome"
        Id = "Google.Chrome"
        Description = "Браузер"
    },
    @{
        Name = "Mozilla Firefox"
        Id = "Mozilla.Firefox"
        Description = "Браузер (уже настроен с VPN)"
    },
    @{
        Name = "Visual Studio Code"
        Id = "Microsoft.VisualStudioCode"
        Description = "Редактор кода"
    },
    @{
        Name = "Git"
        Id = "Git.Git"
        Description = "Система контроля версий"
    },
    @{
        Name = "Python"
        Id = "Python.Python.3.12"
        Description = "Язык программирования"
    },
    @{
        Name = "PowerShell 7"
        Id = "Microsoft.PowerShell"
        Description = "Современная оболочка PowerShell"
    },
    @{
        Name = "VLC Media Player"
        Id = "VideoLAN.VLC"
        Description = "Медиаплеер"
    },
    @{
        Name = "Notepad++"
        Id = "Notepad++.Notepad++"
        Description = "Текстовый редактор"
    },
    @{
        Name = "Discord"
        Id = "Discord.Discord"
        Description = "Мессенджер"
    },
    @{
        Name = "Telegram"
        Id = "Telegram.TelegramDesktop"
        Description = "Мессенджер"
    },
    @{
        Name = "qBittorrent"
        Id = "qBittorrent.qBittorrent"
        Description = "Торрент-клиент"
    },
    @{
        Name = "Everything"
        Id = "voidtools.Everything"
        Description = "Быстрый поиск файлов"
    },
    @{
        Name = "ShareX"
        Id = "ShareX.ShareX"
        Description = "Скриншоты и запись экрана"
    },
    @{
        Name = "Windows Terminal"
        Id = "Microsoft.WindowsTerminal"
        Description = "Современный терминал"
    }
)

$utilityPrograms = @(
    @{
        Name = "CPU-Z"
        Id = "CPUID.CPU-Z"
        Description = "Информация о процессоре"
    },
    @{
        Name = "GPU-Z"
        Id = "TechPowerUp.GPU-Z"
        Description = "Информация о видеокарте"
    },
    @{
        Name = "HWiNFO"
        Id = "REALiX.HWiNFO"
        Description = "Мониторинг системы"
    },
    @{
        Name = "MSI Afterburner"
        Id = "Guru3D.Afterburner"
        Description = "Разгон видеокарты"
    },
    @{
        Name = "CrystalDiskInfo"
        Id = "CrystalDewWorld.CrystalDiskInfo"
        Description = "Проверка дисков"
    }
)

# ========================================
# ИНТЕРАКТИВНЫЙ ВЫБОР
# ========================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ВЫБЕРИТЕ ПРОГРАММЫ ДЛЯ УСТАНОВКИ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "ОСНОВНЫЕ ПРОГРАММЫ:" -ForegroundColor Yellow
Write-Host ""

$toInstall = @()

# Показываем список
for ($i = 0; $i -lt $essentialPrograms.Count; $i++) {
    $prog = $essentialPrograms[$i]
    Write-Host "  [$($i + 1)] $($prog.Name)" -ForegroundColor White
    Write-Host "      $($prog.Description)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host ""
Write-Host "УТИЛИТЫ (опционально):" -ForegroundColor Yellow
Write-Host ""

$startIndex = $essentialPrograms.Count
for ($i = 0; $i -lt $utilityPrograms.Count; $i++) {
    $prog = $utilityPrograms[$i]
    Write-Host "  [$($startIndex + $i + 1)] $($prog.Name)" -ForegroundColor White
    Write-Host "      $($prog.Description)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ВАРИАНТЫ:" -ForegroundColor Yellow
Write-Host "  [A] Установить всё основное" -ForegroundColor White
Write-Host "  [B] Установить всё (основное + утилиты)" -ForegroundColor White
Write-Host "  [C] Выборочная установка (введите номера через пробел, например: 1 2 5)" -ForegroundColor White
Write-Host "  [N] Ничего не устанавливать" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Ваш выбор"

# Обработка выбора
$choice = $choice.ToUpper().Trim()

if ($choice -eq "A") {
    $toInstall = $essentialPrograms
    Write-Host "`n[INFO] Будет установлено: Все основные программы`n" -ForegroundColor Cyan
} elseif ($choice -eq "B") {
    $toInstall = $essentialPrograms + $utilityPrograms
    Write-Host "`n[INFO] Будет установлено: Всё (основное + утилиты)`n" -ForegroundColor Cyan
} elseif ($choice -eq "N") {
    Write-Host "`n[INFO] Установка отменена`n" -ForegroundColor Yellow
    pause
    exit
} elseif ($choice -eq "C") {
    Write-Host ""
    $numbers = Read-Host "Введите номера программ через пробел (например: 1 2 5 10)"
    $selectedIndexes = $numbers.Split(" ") | ForEach-Object { [int]$_ - 1 }
    
    $allPrograms = $essentialPrograms + $utilityPrograms
    foreach ($index in $selectedIndexes) {
        if ($index -ge 0 -and $index -lt $allPrograms.Count) {
            $toInstall += $allPrograms[$index]
        }
    }
    
    if ($toInstall.Count -eq 0) {
        Write-Host "`n[WARN] Ничего не выбрано. Установка отменена.`n" -ForegroundColor Yellow
        pause
        exit
    }
    
    Write-Host "`n[INFO] Будет установлено программ: $($toInstall.Count)`n" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Неверный выбор. Установка отменена.`n" -ForegroundColor Red
    pause
    exit
}

# ========================================
# УСТАНОВКА
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  НАЧАЛО УСТАНОВКИ" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$installed = 0
$failed = 0
$skipped = 0

for ($i = 0; $i -lt $toInstall.Count; $i++) {
    $prog = $toInstall[$i]
    $current = $i + 1
    $total = $toInstall.Count
    
    Write-Host "[$current/$total] Установка $($prog.Name)..." -ForegroundColor Yellow
    
    # Проверка, установлена ли уже
    $existing = winget list --id $prog.Id --exact 2>$null
    if ($LASTEXITCODE -eq 0 -and $existing -match $prog.Id) {
        Write-Host "  [SKIP] Уже установлено" -ForegroundColor Gray
        $skipped++
    } else {
        # Установка
        winget install --id $prog.Id --exact --silent --accept-package-agreements --accept-source-agreements
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Установлено успешно" -ForegroundColor Green
            $installed++
        } else {
            Write-Host "  [ERROR] Ошибка установки" -ForegroundColor Red
            $failed++
        }
    }
    
    Write-Host ""
}

# ========================================
# ИТОГИ
# ========================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "  УСТАНОВКА ЗАВЕРШЕНА!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "СТАТИСТИКА:" -ForegroundColor Cyan
Write-Host "  ✓ Установлено: $installed" -ForegroundColor Green
Write-Host "  - Пропущено (уже установлено): $skipped" -ForegroundColor Gray
if ($failed -gt 0) {
    Write-Host "  ✗ Ошибок: $failed" -ForegroundColor Red
}
Write-Host ""

Write-Host "РЕКОМЕНДАЦИИ:" -ForegroundColor Yellow
Write-Host "  1. Перезагрузите компьютер для применения всех изменений" -ForegroundColor White
Write-Host "  2. Настройте установленные программы под себя" -ForegroundColor White
Write-Host "  3. Проверьте автозапуск программ (Ctrl+Shift+Esc → Автозагрузка)" -ForegroundColor White
Write-Host ""

pause
