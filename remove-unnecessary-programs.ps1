# Remove Unnecessary Programs from Windows
# Run as Administrator for full cleanup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Удаление ненужных программ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[WARN] Некоторые операции требуют прав администратора" -ForegroundColor Yellow
    Write-Host "[INFO] Запустите скрипт от имени администратора для полной очистки" -ForegroundColor Gray
    Write-Host ""
}

# Step 1: Remove unnecessary UWP apps
Write-Host "[1/6] Удаление ненужных UWP приложений..." -ForegroundColor Yellow

$appsToRemove = @(
    # Xbox apps
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.Xbox.TCUI",
    "Microsoft.XboxGameCallableUI",
    "Microsoft.GamingApp",
    
    # Bing apps
    "Microsoft.BingNews",
    "Microsoft.BingWeather",
    "Microsoft.BingFinance",
    "Microsoft.BingSports",
    
    # Office and productivity
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.MicrosoftOfficeHub",
    "Microsoft.MicrosoftStickyNotes",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "Microsoft.Todos",
    
    # Communication
    "Microsoft.People",
    "Microsoft.SkypeApp",
    "Microsoft.YourPhone",
    "microsoft.windowscommunicationsapps",  # Mail & Calendar
    
    # Media
    "Microsoft.ZuneMusic",
    "Microsoft.ZuneVideo",
    "Microsoft.MixedReality.Portal",
    
    # Utilities
    "Microsoft.3DBuilder",
    "Microsoft.WindowsMaps",
    "Microsoft.WindowsAlarms",
    "Microsoft.WindowsCamera",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.WindowsSoundRecorder",
    "Microsoft.WindowsCalculator",  # If you don't need it
    
    # Other
    "Microsoft.MicrosoftEdge.Stable",  # If you use other browser
    "Microsoft.MicrosoftEdgeDevToolsClient",
    "Microsoft.Edge.GameAssist",
    "Microsoft.StartExperiencesApp",
    "Microsoft.Windows.ContentDeliveryManager",
    
    # Third-party unnecessary
    "1527c705-839a-4832-9118-54d4Bd6a0c89",
    "325289AEDD75.TorrentRTFREE",
    "A025C540.Yandex.Music",
    "c5e2524a-ea46-4f67-841f-6a9465d9d515",
    "E2A4F912-2574-4A75-9BB0-0D023378592B",
    "F46D4000-FD22-4DB4-AC8E-4E1DDDE828FE",
    
    # Windows widgets (if not needed)
    "Microsoft.WidgetsPlatformRuntime",
    "MicrosoftWindows.57242383.Tasbar",
    "MicrosoftWindows.59336768.Speion",
    "MicrosoftWindows.59337133.Voiess",
    "MicrosoftWindows.59337145.Livtop",
    "MicrosoftWindows.59379618.InpApp"
)

$removed = 0
$failed = 0

foreach ($app in $appsToRemove) {
    $package = Get-AppxPackage -Name $app -ErrorAction SilentlyContinue
    if ($package) {
        try {
            Write-Host "  Удаляю: $app" -ForegroundColor Gray
            Remove-AppxPackage -Package $package.PackageFullName -ErrorAction Stop
            $removed++
        } catch {
            Write-Host "  [WARN] Не удалось удалить: $app" -ForegroundColor Yellow
            $failed++
        }
    }
}

# Also remove for all users (if admin)
if ($isAdmin) {
    foreach ($app in $appsToRemove) {
        $provisioned = Get-AppxProvisionedPackage -Online | Where-Object { $_.DisplayName -like "*$app*" } -ErrorAction SilentlyContinue
        if ($provisioned) {
            try {
                Write-Host "  Удаляю для всех пользователей: $app" -ForegroundColor Gray
                Remove-AppxProvisionedPackage -Online -PackageName $provisioned.PackageName -ErrorAction Stop
            } catch {
                # Ignore errors
            }
        }
    }
}

if ($removed -gt 0) {
    Write-Host "  [OK] Удалено $removed приложений" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ненужные приложения не найдены" -ForegroundColor Green
}

if ($failed -gt 0) {
    Write-Host "  [WARN] Не удалось удалить $failed приложений" -ForegroundColor Yellow
}

Write-Host ""

# Step 2: Remove desktop shortcuts
Write-Host "[2/6] Удаление ненужных ярлыков с рабочего стола..." -ForegroundColor Yellow
$desktop = [Environment]::GetFolderPath("Desktop")
$publicDesktop = [Environment]::GetFolderPath("CommonDesktopDirectory")

$shortcutsToRemove = @(
    "*Microsoft Edge*",
    "*Office*",
    "*Skype*",
    "*Xbox*",
    "*Get Started*",
    "*Mail*",
    "*Calendar*",
    "*OneDrive*",
    "*Teams*"
)

$removedShortcuts = 0
foreach ($path in @($desktop, $publicDesktop)) {
    if (Test-Path $path) {
        foreach ($pattern in $shortcutsToRemove) {
            $files = Get-ChildItem -Path $path -Filter $pattern -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                try {
                    Write-Host "  Удаляю: $($file.Name)" -ForegroundColor Gray
                    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
                    $removedShortcuts++
                } catch {
                    Write-Host "  [WARN] Не удалось удалить: $($file.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedShortcuts -gt 0) {
    Write-Host "  [OK] Удалено $removedShortcuts ярлыков" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ненужные ярлыки не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 3: Remove Start Menu shortcuts
Write-Host "[3/6] Удаление ярлыков из меню Пуск..." -ForegroundColor Yellow
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$commonStartMenu = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"

$removedStartMenu = 0
foreach ($path in @($startMenu, $commonStartMenu)) {
    if (Test-Path $path) {
        foreach ($pattern in $shortcutsToRemove) {
            $files = Get-ChildItem -Path $path -Filter $pattern -Recurse -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                try {
                    Write-Host "  Удаляю: $($file.Name)" -ForegroundColor Gray
                    Remove-Item -Path $file.FullName -Force -ErrorAction SilentlyContinue
                    $removedStartMenu++
                } catch {
                    Write-Host "  [WARN] Не удалось удалить: $($file.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedStartMenu -gt 0) {
    Write-Host "  [OK] Удалено $removedStartMenu ярлыков из меню Пуск" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ненужные ярлыки не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 4: Clean startup programs
Write-Host "[4/6] Очистка автозапуска..." -ForegroundColor Yellow
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$commonStartupPath = "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"

# Programs to keep
$keepInStartup = @("Hysteria2", "hysteria2", "Ollama")

# Programs to remove
$unnecessaryStartup = @("Skype", "Xbox", "Teams", "Discord", "Steam", "Spotify", "OneDrive")

$removedStartup = 0
foreach ($path in @($startupPath, $commonStartupPath)) {
    if (Test-Path $path) {
        $items = Get-ChildItem -Path $path -ErrorAction SilentlyContinue
        foreach ($item in $items) {
            $shouldKeep = $false
            foreach ($keep in $keepInStartup) {
                if ($item.Name -like "*$keep*") {
                    $shouldKeep = $true
                    break
                }
            }
            
            if (-not $shouldKeep) {
                $isUnnecessary = $false
                foreach ($unwanted in $unnecessaryStartup) {
                    if ($item.Name -like "*$unwanted*") {
                        $isUnnecessary = $true
                        break
                    }
                }
                
                if ($isUnnecessary) {
                    try {
                        Write-Host "  Удаляю из автозапуска: $($item.Name)" -ForegroundColor Gray
                        Remove-Item -Path $item.FullName -Force -ErrorAction SilentlyContinue
                        $removedStartup++
                    } catch {
                        Write-Host "  [WARN] Не удалось удалить: $($item.Name)" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
}

# Registry startup
$registryStartup = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    foreach ($key in $regKeys) {
        $shouldKeep = $false
        foreach ($keep in $keepInStartup) {
            if ($key.Name -like "*$keep*" -or $key.Value -like "*$keep*") {
                $shouldKeep = $true
                break
            }
        }
        
        if (-not $shouldKeep) {
            $isUnnecessary = $false
            foreach ($unwanted in $unnecessaryStartup) {
                if ($key.Name -like "*$unwanted*" -or $key.Value -like "*$unwanted*") {
                    $isUnnecessary = $true
                    break
                }
            }
            
            if ($isUnnecessary) {
                try {
                    Write-Host "  Удаляю из реестра: $($key.Name)" -ForegroundColor Gray
                    Remove-ItemProperty -Path $registryStartup -Name $key.Name -ErrorAction SilentlyContinue
                    $removedStartup++
                } catch {
                    Write-Host "  [WARN] Не удалось удалить: $($key.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

if ($removedStartup -gt 0) {
    Write-Host "  [OK] Удалено $removedStartup программ из автозапуска" -ForegroundColor Green
} else {
    Write-Host "  [OK] Ненужные программы в автозапуске не найдены" -ForegroundColor Green
}

Write-Host ""

# Step 5: Show remaining programs
Write-Host "[5/6] Оставшиеся программы в автозапуске:" -ForegroundColor Yellow
Write-Host ""

$regItems = Get-ItemProperty -Path $registryStartup -ErrorAction SilentlyContinue
if ($regItems) {
    $regKeys = $regItems.PSObject.Properties | Where-Object { $_.Name -notlike "PS*" }
    if ($regKeys) {
        foreach ($key in $regKeys) {
            Write-Host "  - $($key.Name)" -ForegroundColor White
        }
    } else {
        Write-Host "  (нет)" -ForegroundColor Gray
    }
} else {
    Write-Host "  (нет)" -ForegroundColor Gray
}

Write-Host ""

# Step 6: Summary
Write-Host "[6/6] Итоги очистки..." -ForegroundColor Yellow
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Очистка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "УДАЛЕНО:" -ForegroundColor Yellow
Write-Host "  - UWP приложений: $removed" -ForegroundColor White
Write-Host "  - Ярлыков с рабочего стола: $removedShortcuts" -ForegroundColor White
Write-Host "  - Ярлыков из меню Пуск: $removedStartMenu" -ForegroundColor White
Write-Host "  - Программ из автозапуска: $removedStartup" -ForegroundColor White
Write-Host ""
Write-Host "ЧТО ОСТАЛОСЬ В АВТОЗАПУСКЕ:" -ForegroundColor Cyan
Write-Host "  - Hysteria2 VPN (важно!)" -ForegroundColor White
Write-Host "  - Ollama (если настроен)" -ForegroundColor White
Write-Host ""
Write-Host "УПРАВЛЕНИЕ АВТОЗАПУСКОМ:" -ForegroundColor Yellow
Write-Host "  Диспетчер задач → Вкладка 'Автозагрузка'" -ForegroundColor White
Write-Host "  Или: Параметры → Приложения → Автозагрузка" -ForegroundColor White
Write-Host ""

