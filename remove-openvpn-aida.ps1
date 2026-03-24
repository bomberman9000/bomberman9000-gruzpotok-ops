# Remove OpenVPN-GUI and AIDA64
# Run as Administrator for full removal

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Удаление OpenVPN-GUI и AIDA64" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARN] Для полного удаления требуются права администратора" -ForegroundColor Yellow
    Write-Host "[INFO] Запустите скрипт от имени администратора" -ForegroundColor Gray
    Write-Host ""
}

# Step 1: Find and remove OpenVPN-GUI
Write-Host "[1/4] Поиск OpenVPN-GUI..." -ForegroundColor Yellow

$openvpnFound = $false
$registryPaths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$openvpnApps = @()
foreach ($path in $registryPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { 
        $_.DisplayName -like "*OpenVPN*" 
    }
    if ($apps) {
        $openvpnApps += $apps
    }
}

if ($openvpnApps) {
    $openvpnFound = $true
    foreach ($app in $openvpnApps) {
        Write-Host "  Найдено: $($app.DisplayName)" -ForegroundColor Green
        Write-Host "    Путь: $($app.InstallLocation)" -ForegroundColor Gray
        
        if ($app.UninstallString) {
            Write-Host "  Удаляю..." -ForegroundColor Yellow
            
            # Extract uninstall command
            $uninstallCmd = $app.UninstallString
            if ($uninstallCmd -match '^"(.+)"') {
                $exe = $matches[1]
                $args = $uninstallCmd.Substring($matches[0].Length).Trim()
            } elseif ($uninstallCmd -match '^(.+\.exe)') {
                $exe = $matches[1]
                $args = $uninstallCmd.Substring($matches[0].Length).Trim()
            } else {
                $exe = $uninstallCmd
                $args = "/S"  # Silent uninstall
            }
            
            # Add silent flag if not present
            if ($args -notmatch '/S|/SILENT|/VERYSILENT') {
                $args = "/S " + $args
            }
            
            try {
                if (Test-Path $exe) {
                    Start-Process -FilePath $exe -ArgumentList $args -Wait -NoNewWindow -ErrorAction Stop
                    Write-Host "  [OK] OpenVPN-GUI удален" -ForegroundColor Green
                } else {
                    Write-Host "  [WARN] Файл удаления не найден: $exe" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "  [ERROR] Не удалось удалить: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  [WARN] Команда удаления не найдена" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [INFO] OpenVPN-GUI не найден в реестре" -ForegroundColor Gray
}

# Also check for OpenVPN in startup
Write-Host ""
Write-Host "  Проверка автозапуска..." -ForegroundColor Gray
$registryStartup = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { 
        $_.Name -notlike "PS*" -and ($_.Name -like "*OpenVPN*" -or $_.Value -like "*OpenVPN*")
    }
    foreach ($key in $regKeys) {
        try {
            Write-Host "  Удаляю из автозапуска: $($key.Name)" -ForegroundColor Gray
            Remove-ItemProperty -Path $registryStartup -Name $key.Name -ErrorAction Stop
            Write-Host "  [OK] Удалено из автозапуска" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Не удалось удалить из автозапуска: $_" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# Step 2: Find and remove AIDA64
Write-Host "[2/4] Поиск AIDA64..." -ForegroundColor Yellow

$aidaFound = $false
$aidaApps = @()
foreach ($path in $registryPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { 
        $_.DisplayName -like "*AIDA*" 
    }
    if ($apps) {
        $aidaApps += $apps
    }
}

if ($aidaApps) {
    $aidaFound = $true
    foreach ($app in $aidaApps) {
        Write-Host "  Найдено: $($app.DisplayName)" -ForegroundColor Green
        Write-Host "    Путь: $($app.InstallLocation)" -ForegroundColor Gray
        
        if ($app.UninstallString) {
            Write-Host "  Удаляю..." -ForegroundColor Yellow
            
            # Extract uninstall command
            $uninstallCmd = $app.UninstallString
            if ($uninstallCmd -match '^"(.+)"') {
                $exe = $matches[1]
                $args = $uninstallCmd.Substring($matches[0].Length).Trim()
            } elseif ($uninstallCmd -match '^(.+\.exe)') {
                $exe = $matches[1]
                $args = $uninstallCmd.Substring($matches[0].Length).Trim()
            } else {
                $exe = $uninstallCmd
                $args = "/S"  # Silent uninstall
            }
            
            # Add silent flag if not present
            if ($args -notmatch '/S|/SILENT|/VERYSILENT') {
                $args = "/S " + $args
            }
            
            try {
                if (Test-Path $exe) {
                    Start-Process -FilePath $exe -ArgumentList $args -Wait -NoNewWindow -ErrorAction Stop
                    Write-Host "  [OK] AIDA64 удален" -ForegroundColor Green
                } else {
                    Write-Host "  [WARN] Файл удаления не найден: $exe" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "  [ERROR] Не удалось удалить: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  [WARN] Команда удаления не найдена" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [INFO] AIDA64 не найден в реестре" -ForegroundColor Gray
}

# Also check for AIDA64 in startup
Write-Host ""
Write-Host "  Проверка автозапуска..." -ForegroundColor Gray
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { 
        $_.Name -notlike "PS*" -and ($_.Name -like "*AIDA*" -or $_.Value -like "*AIDA*")
    }
    foreach ($key in $regKeys) {
        try {
            Write-Host "  Удаляю из автозапуска: $($key.Name)" -ForegroundColor Gray
            Remove-ItemProperty -Path $registryStartup -Name $key.Name -ErrorAction Stop
            Write-Host "  [OK] Удалено из автозапуска" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Не удалось удалить из автозапуска: $_" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# Step 3: Remove shortcuts
Write-Host "[3/4] Удаление ярлыков..." -ForegroundColor Yellow

$shortcutsPaths = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("CommonDesktopDirectory"),
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
)

$removedShortcuts = 0
foreach ($path in $shortcutsPaths) {
    if (Test-Path $path) {
        $shortcuts = Get-ChildItem -Path $path -Recurse -Filter "*OpenVPN*" -ErrorAction SilentlyContinue
        $shortcuts += Get-ChildItem -Path $path -Recurse -Filter "*AIDA*" -ErrorAction SilentlyContinue
        
        foreach ($shortcut in $shortcuts) {
            try {
                Write-Host "  Удаляю: $($shortcut.Name)" -ForegroundColor Gray
                Remove-Item -Path $shortcut.FullName -Force -ErrorAction SilentlyContinue
                $removedShortcuts++
            } catch {
                Write-Host "  [WARN] Не удалось удалить: $($shortcut.Name)" -ForegroundColor Yellow
            }
        }
    }
}

if ($removedShortcuts -gt 0) {
    Write-Host "  [OK] Удалено $removedShortcuts ярлыков" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ярлыки не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 4: Clean up processes
Write-Host "[4/4] Остановка процессов..." -ForegroundColor Yellow

$processes = Get-Process | Where-Object { 
    $_.ProcessName -like "*OpenVPN*" -or 
    $_.ProcessName -like "*AIDA*" 
}

if ($processes) {
    foreach ($proc in $processes) {
        try {
            Write-Host "  Останавливаю: $($proc.ProcessName)" -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            Write-Host "  [OK] Процесс остановлен" -ForegroundColor Green
        } catch {
            Write-Host "  [WARN] Не удалось остановить: $($proc.ProcessName)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  [OK] Процессы не запущены" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Удаление завершено!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ИТОГИ:" -ForegroundColor Yellow
if ($openvpnFound) {
    Write-Host "  ✓ OpenVPN-GUI найден и удален" -ForegroundColor Green
} else {
    Write-Host "  ℹ OpenVPN-GUI не найден" -ForegroundColor Gray
}

if ($aidaFound) {
    Write-Host "  ✓ AIDA64 найден и удален" -ForegroundColor Green
} else {
    Write-Host "  ℹ AIDA64 не найден" -ForegroundColor Gray
}

Write-Host "  ✓ Ярлыков удалено: $removedShortcuts" -ForegroundColor White
Write-Host ""
Write-Host "ПРИМЕЧАНИЕ:" -ForegroundColor Cyan
Write-Host "  Если программы не удалились автоматически," -ForegroundColor White
Write-Host "  удалите их вручную через:" -ForegroundColor White
Write-Host "  Параметры → Приложения → Установленные приложения" -ForegroundColor Gray
Write-Host ""

