# Remove Lesta Installer and All Files
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "УДАЛЕНИЕ LESTA" -ForegroundColor Cyan
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

# Step 1: Stop Lesta processes
Write-Host "[1/5] Остановка процессов Lesta..." -ForegroundColor Yellow

$lestaProcesses = @("Wargaming*", "WorldOfTanks*", "WorldOfWarships*", "WoT*", "WoWS*", "Lesta*")
$stopped = 0

foreach ($procPattern in $lestaProcesses) {
    $processes = Get-Process -Name $procPattern -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        try {
            Write-Host "  Останавливаю: $($proc.ProcessName)" -ForegroundColor Gray
            Stop-Process -Id $proc.Id -Force -ErrorAction Stop
            $stopped++
        } catch {
            # Continue
        }
    }
}

if ($stopped -gt 0) {
    Write-Host "  [OK] Остановлено процессов: $stopped" -ForegroundColor Green
} else {
    Write-Host "  [OK] Процессы Lesta не запущены" -ForegroundColor Green
}

Write-Host ""

# Step 2: Uninstall from registry
Write-Host "[2/5] Удаление через установщик Windows..." -ForegroundColor Yellow

$lestaPrograms = Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*" -ErrorAction SilentlyContinue | Where-Object {
    $_.DisplayName -like "*Lesta*" -or
    $_.DisplayName -like "*World of Tanks*" -or
    $_.DisplayName -like "*World of Warships*" -or
    $_.Publisher -like "*Lesta*" -or
    $_.Publisher -like "*Wargaming*"
}

$removed = 0
foreach ($item in $lestaPrograms) {
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
                Start-Process -FilePath $exe -ArgumentList $args -Wait -NoNewWindow -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
                Write-Host "  [OK] Удалено: $($item.DisplayName)" -ForegroundColor Green
                $removed++
            }
        } catch {
            Write-Host "  [WARN] Ошибка при удалении: $_" -ForegroundColor Yellow
        }
    }
}

if ($removed -gt 0) {
    Write-Host "  [OK] Удалено программ: $removed" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Программы Lesta не найдены в установщике" -ForegroundColor Gray
}

Write-Host ""

# Step 3: Remove Lesta folders
Write-Host "[3/5] Удаление папок Lesta..." -ForegroundColor Yellow

$foldersToRemove = @(
    "C:\Program Files\Lesta",
    "C:\Program Files (x86)\Lesta",
    "C:\Program Files\Wargaming.net",
    "C:\Program Files (x86)\Wargaming.net",
    "C:\Program Files\World_of_Tanks",
    "C:\Program Files (x86)\World_of_Tanks",
    "C:\Program Files\World_of_Warships",
    "C:\Program Files (x86)\World_of_Warships",
    "$env:APPDATA\Lesta",
    "$env:APPDATA\Wargaming.net",
    "$env:LOCALAPPDATA\Lesta",
    "$env:LOCALAPPDATA\Wargaming.net",
    "$env:ProgramData\Lesta",
    "$env:ProgramData\Wargaming.net",
    "$env:USERPROFILE\Documents\World_of_Tanks",
    "$env:USERPROFILE\Documents\World_of_Warships"
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
            Write-Host "         (файлы могут быть заблокированы)" -ForegroundColor Gray
        }
    }
}

if ($removedFolders -gt 0) {
    Write-Host "  [OK] Удалено папок: $removedFolders" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Папки Lesta не найдены" -ForegroundColor Gray
}

Write-Host ""

# Step 4: Find and remove installers
Write-Host "[4/5] Поиск и удаление установщиков..." -ForegroundColor Yellow

$installerPaths = @(
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Desktop",
    "$env:USERPROFILE\Documents"
)

$removedFiles = 0
foreach ($path in $installerPaths) {
    if (Test-Path $path) {
        $files = Get-ChildItem $path -File -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -like "*Lesta*" -or
            $_.Name -like "*Wargaming*" -or
            $_.Name -like "*WorldOfTanks*" -or
            $_.Name -like "*WorldOfWarships*" -or
            $_.Name -like "*WoT*" -or
            $_.Name -like "*WoWS*"
        }
        
        foreach ($file in $files) {
            try {
                Write-Host "  Удаляю: $($file.Name)" -ForegroundColor Gray
                Remove-Item -Path $file.FullName -Force -ErrorAction Stop
                Write-Host "  [OK] Удалено" -ForegroundColor Green
                $removedFiles++
            } catch {
                Write-Host "  [WARN] Не удалось удалить: $($file.Name)" -ForegroundColor Yellow
            }
        }
    }
}

if ($removedFiles -gt 0) {
    Write-Host "  [OK] Удалено файлов: $removedFiles" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Установщики не найдены" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Clean registry
Write-Host "[5/5] Очистка реестра..." -ForegroundColor Yellow

$regKeysToRemove = @(
    "HKLM:\Software\Lesta",
    "HKLM:\Software\Wargaming.net",
    "HKLM:\Software\Wow6432Node\Lesta",
    "HKLM:\Software\Wow6432Node\Wargaming.net",
    "HKCU:\Software\Lesta",
    "HKCU:\Software\Wargaming.net"
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
    Write-Host "  [INFO] Ключи реестра не найдены" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "УДАЛЕНИЕ ЗАВЕРШЕНО!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "ИТОГИ:" -ForegroundColor Yellow
Write-Host "  - Остановлено процессов: $stopped" -ForegroundColor White
Write-Host "  - Удалено программ: $removed" -ForegroundColor White
Write-Host "  - Удалено папок: $removedFolders" -ForegroundColor White
Write-Host "  - Удалено файлов: $removedFiles" -ForegroundColor White
Write-Host "  - Удалено ключей реестра: $removedKeys" -ForegroundColor White
Write-Host ""
Write-Host "РЕКОМЕНДАЦИЯ:" -ForegroundColor Cyan
Write-Host "  Перезагрузите компьютер для полной очистки" -ForegroundColor White
Write-Host ""

pause





