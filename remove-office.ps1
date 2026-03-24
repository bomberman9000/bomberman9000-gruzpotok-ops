# Remove Microsoft Office Completely
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Удаление Microsoft Office" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Требуются права администратора!" -ForegroundColor Red
    Write-Host "[INFO] Запустите PowerShell от имени администратора" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Step 1: Find Office installations
Write-Host "[1/6] Поиск установок Office..." -ForegroundColor Yellow

$officePaths = @()
$searchPaths = @(
    "C:\Program Files\Microsoft Office",
    "C:\Program Files (x86)\Microsoft Office"
)

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath) {
        $versions = Get-ChildItem $basePath -Directory -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $officePaths += $version.FullName
            Write-Host "  Найдено: $($version.FullName)" -ForegroundColor Green
        }
    }
}

# Check registry for Office
$regPaths = @(
    "HKLM:\Software\Microsoft\Office",
    "HKLM:\Software\Wow6432Node\Microsoft\Office"
)

$officeProducts = @()
foreach ($regPath in $regPaths) {
    if (Test-Path $regPath) {
        $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $uninstallPath = Join-Path $version.PSPath "Common\InstallRoot"
            if (Test-Path $uninstallPath) {
                $officeProducts += $version
            }
        }
    }
}

# Check uninstall registry
$uninstallKeys = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$officeUninstall = @()
foreach ($keyPath in $uninstallKeys) {
    $items = Get-ItemProperty $keyPath -ErrorAction SilentlyContinue | Where-Object {
        $_.DisplayName -like "*Microsoft Office*" -or
        $_.DisplayName -like "*Office 2016*" -or
        $_.DisplayName -like "*Office 2019*" -or
        $_.DisplayName -like "*Office 2021*" -or
        $_.DisplayName -like "*Office 365*"
    }
    if ($items) {
        $officeUninstall += $items
    }
}

if ($officeUninstall.Count -eq 0 -and $officePaths.Count -eq 0) {
    Write-Host "  [INFO] Office не найден в системе" -ForegroundColor Gray
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Office не установлен" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    pause
    exit 0
}

Write-Host "  [OK] Найдено установок: $($officeUninstall.Count)" -ForegroundColor Green
Write-Host ""

# Step 2: Stop Office processes
Write-Host "[2/6] Остановка процессов Office..." -ForegroundColor Yellow

$officeProcesses = @("winword", "excel", "powerpnt", "outlook", "msaccess", "onenote", "lync", "mspub", "visio", "winproj")
$stopped = 0

foreach ($procName in $officeProcesses) {
    $processes = Get-Process -Name $procName -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        try {
            Write-Host "  Останавливаю: $($proc.ProcessName)" -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            $stopped++
        } catch {
            Write-Host "  [WARN] Не удалось остановить: $($proc.ProcessName)" -ForegroundColor Yellow
        }
    }
}

if ($stopped -gt 0) {
    Write-Host "  [OK] Остановлено процессов: $stopped" -ForegroundColor Green
} else {
    Write-Host "  [OK] Процессы Office не запущены" -ForegroundColor Green
}

Write-Host ""

# Step 3: Uninstall via registry
Write-Host "[3/6] Удаление через установщик Windows..." -ForegroundColor Yellow

$removed = 0
foreach ($item in $officeUninstall) {
    if ($item.UninstallString) {
        Write-Host "  Удаляю: $($item.DisplayName)" -ForegroundColor Gray
        
        $uninstallCmd = $item.UninstallString
        
        # Extract executable and arguments
        if ($uninstallCmd -match '^"(.+)"') {
            $exe = $matches[1]
            $args = $uninstallCmd.Substring($matches[0].Length).Trim()
        } elseif ($uninstallCmd -match '^(.+\.exe)') {
            $exe = $matches[1]
            $args = $uninstallCmd.Substring($matches[0].Length).Trim()
        } else {
            $exe = $uninstallCmd
            $args = "/S"
        }
        
        # Add silent flag if not present
        if ($args -notmatch '/S|/SILENT|/VERYSILENT|/quiet') {
            if ($args) {
                $args = "/S " + $args
            } else {
                $args = "/S"
            }
        }
        
        try {
            if (Test-Path $exe) {
                Start-Process -FilePath $exe -ArgumentList $args -Wait -NoNewWindow -ErrorAction Stop
                Start-Sleep -Seconds 3
                Write-Host "  [OK] Удалено: $($item.DisplayName)" -ForegroundColor Green
                $removed++
            } else {
                Write-Host "  [WARN] Файл удаления не найден: $exe" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [ERROR] Ошибка при удалении: $_" -ForegroundColor Red
        }
    }
}

if ($removed -gt 0) {
    Write-Host "  [OK] Удалено программ: $removed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Не удалось удалить через установщик" -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Remove Office folders
Write-Host "[4/6] Удаление папок Office..." -ForegroundColor Yellow

$foldersToRemove = @(
    "C:\Program Files\Microsoft Office",
    "C:\Program Files (x86)\Microsoft Office",
    "$env:APPDATA\Microsoft\Office",
    "$env:LOCALAPPDATA\Microsoft\Office",
    "$env:ProgramData\Microsoft\Office"
)

$removedFolders = 0
foreach ($folder in $foldersToRemove) {
    if (Test-Path $folder) {
        try {
            Write-Host "  Удаляю: $folder" -ForegroundColor Gray
            Remove-Item -Path $folder -Recurse -Force -ErrorAction Stop
            Write-Host "  [OK] Удалено" -ForegroundColor Green
            $removedFolders++
        } catch {
            Write-Host "  [WARN] Не удалось удалить: $folder" -ForegroundColor Yellow
        }
    }
}

if ($removedFolders -gt 0) {
    Write-Host "  [OK] Удалено папок: $removedFolders" -ForegroundColor Green
} else {
    Write-Host "  [OK] Папки Office не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 5: Clean registry
Write-Host "[5/6] Очистка реестра..." -ForegroundColor Yellow

$regKeysToRemove = @(
    "HKLM:\Software\Microsoft\Office",
    "HKLM:\Software\Wow6432Node\Microsoft\Office",
    "HKCU:\Software\Microsoft\Office"
)

$removedKeys = 0
foreach ($regKey in $regKeysToRemove) {
    if (Test-Path $regKey) {
        try {
            Write-Host "  Удаляю: $regKey" -ForegroundColor Gray
            Remove-Item -Path $regKey -Recurse -Force -ErrorAction Stop
            Write-Host "  [OK] Удалено" -ForegroundColor Green
            $removedKeys++
        } catch {
            Write-Host "  [WARN] Не удалось удалить: $regKey" -ForegroundColor Yellow
        }
    }
}

if ($removedKeys -gt 0) {
    Write-Host "  [OK] Удалено ключей реестра: $removedKeys" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ключи реестра не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 6: Remove shortcuts
Write-Host "[6/6] Удаление ярлыков..." -ForegroundColor Yellow

$shortcutPaths = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("CommonDesktopDirectory"),
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
)

$removedShortcuts = 0
$shortcutPatterns = @("*Word*", "*Excel*", "*PowerPoint*", "*Outlook*", "*Access*", "*OneNote*", "*Publisher*", "*Office*")

foreach ($path in $shortcutPaths) {
    if (Test-Path $path) {
        foreach ($pattern in $shortcutPatterns) {
            $shortcuts = Get-ChildItem -Path $path -Filter $pattern -Recurse -ErrorAction SilentlyContinue
            foreach ($shortcut in $shortcuts) {
                try {
                    Remove-Item -Path $shortcut.FullName -Force -ErrorAction SilentlyContinue
                    $removedShortcuts++
                } catch {
                    # Ignore
                }
            }
        }
    }
}

if ($removedShortcuts -gt 0) {
    Write-Host "  [OK] Удалено ярлыков: $removedShortcuts" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ярлыки не найдены" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Удаление завершено!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ИТОГИ:" -ForegroundColor Yellow
Write-Host "  - Остановлено процессов: $stopped" -ForegroundColor White
Write-Host "  - Удалено программ: $removed" -ForegroundColor White
Write-Host "  - Удалено папок: $removedFolders" -ForegroundColor White
Write-Host "  - Удалено ключей реестра: $removedKeys" -ForegroundColor White
Write-Host "  - Удалено ярлыков: $removedShortcuts" -ForegroundColor White
Write-Host ""
Write-Host "РЕКОМЕНДАЦИЯ:" -ForegroundColor Cyan
Write-Host "  Перезагрузите компьютер для полной очистки" -ForegroundColor White
Write-Host ""

pause

