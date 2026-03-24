# Universal Office Activation Script
# Works with Office 2016, 2019, 2021, 365
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Активация Microsoft Office (Универсальная)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Требуются права администратора!" -ForegroundColor Red
    Write-Host "[INFO] Запустите PowerShell от имени администратора" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Правильный способ:" -ForegroundColor Cyan
    Write-Host "1. Правый клик на PowerShell" -ForegroundColor White
    Write-Host "2. Выберите 'Запуск от имени администратора'" -ForegroundColor White
    Write-Host "3. Выполните: cd C:\Users\Shata\project" -ForegroundColor White
    Write-Host "4. Выполните: .\activate-office-universal.ps1" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Step 1: Find Office installation
Write-Host "[1/6] Поиск установки Office..." -ForegroundColor Yellow

$osppPaths = @()
$searchPaths = @(
    "C:\Program Files\Microsoft Office",
    "C:\Program Files (x86)\Microsoft Office",
    "C:\Program Files\Microsoft Office 15",
    "C:\Program Files\Microsoft Office 16",
    "C:\Program Files (x86)\Microsoft Office 15",
    "C:\Program Files (x86)\Microsoft Office 16"
)

foreach ($basePath in $searchPaths) {
    if (Test-Path $basePath) {
        $versions = Get-ChildItem $basePath -Directory -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $ospp16 = Join-Path $version.FullName "Office16\OSPP.VBS"
            $ospp15 = Join-Path $version.FullName "Office15\OSPP.VBS"
            
            if (Test-Path $ospp16) {
                $osppPaths += $ospp16
                Write-Host "  [OK] Найден Office 16: $ospp16" -ForegroundColor Green
            }
            if (Test-Path $ospp15) {
                $osppPaths += $ospp15
                Write-Host "  [OK] Найден Office 15: $ospp15" -ForegroundColor Green
            }
        }
    }
}

# Also check registry
$regPaths = @(
    "HKLM:\Software\Microsoft\Office",
    "HKLM:\Software\Wow6432Node\Microsoft\Office"
)

foreach ($regPath in $regPaths) {
    if (Test-Path $regPath) {
        $versions = Get-ChildItem $regPath -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $commonPath = Join-Path $version.PSPath "Common\InstallRoot"
            if (Test-Path $commonPath) {
                $installRoot = (Get-ItemProperty $commonPath).Path
                if ($installRoot) {
                    $ospp16 = Join-Path $installRoot "Office16\OSPP.VBS"
                    $ospp15 = Join-Path $installRoot "Office15\OSPP.VBS"
                    
                    if (Test-Path $ospp16) { $osppPaths += $ospp16 }
                    if (Test-Path $ospp15) { $osppPaths += $ospp15 }
                }
            }
        }
    }
}

if ($osppPaths.Count -eq 0) {
    Write-Host "  [ERROR] Office не найден!" -ForegroundColor Red
    Write-Host "  [INFO] Возможные причины:" -ForegroundColor Yellow
    Write-Host "    - Office не установлен" -ForegroundColor White
    Write-Host "    - Office установлен в нестандартном месте" -ForegroundColor White
    Write-Host "    - Это Office 365 (требует другой метод активации)" -ForegroundColor White
    Write-Host ""
    Write-Host "  Попробуйте:" -ForegroundColor Cyan
    Write-Host "    1. Установить Office через Microsoft Store" -ForegroundColor White
    Write-Host "    2. Использовать лицензионный ключ" -ForegroundColor White
    Write-Host "    3. Войти в учетную запись Microsoft в Office" -ForegroundColor White
    Write-Host ""
    exit 1
}

$osppPath = $osppPaths[0]
Write-Host "  [OK] Используется: $osppPath" -ForegroundColor Green
Write-Host ""

# Step 2: Check current status
Write-Host "[2/6] Проверка текущего статуса..." -ForegroundColor Yellow
try {
    $status = cscript.exe //nologo "`"$osppPath`"" /dstatus 2>&1
    $status | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} catch {
    Write-Host "  [WARN] Не удалось проверить статус" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Install KMS key
Write-Host "[3/6] Установка KMS ключа..." -ForegroundColor Yellow

$kmsKeys = @(
    "FXYTK-NJJ8C-GB6DW-3DYQT-6F7TH",
    "KDX7X-BNVR8-TXXGX-4Q7Y8-78VT3",
    "NMMKJ-6RK4F-KMJVX-8D9MJ-6MWKP",
    "6NWWJ-YQWMR-QKGCB-6TMB3-9D9HK",
    "XQNVK-8JYDB-WJ9W3-YJ8YR-WFG99",
    "JNRGM-WHDWX-FJJG3-K47QV-DRTFM"
)

$keyInstalled = $false
foreach ($key in $kmsKeys) {
    try {
        Write-Host "  Пробую ключ: $key" -ForegroundColor Gray
        $result = cscript.exe //nologo "`"$osppPath`"" /inpkey:$key 2>&1
        if ($result -match "successful|успешно|Successfully|Installed") {
            Write-Host "  [OK] Ключ установлен: $key" -ForegroundColor Green
            $keyInstalled = $true
            Start-Sleep -Seconds 2
            break
        }
    } catch {
        # Continue
    }
}

if (-not $keyInstalled) {
    Write-Host "  [WARN] Не удалось установить ключ автоматически" -ForegroundColor Yellow
    Write-Host "  [INFO] Продолжаю с существующим ключом" -ForegroundColor Gray
}

Write-Host ""

# Step 4: Set KMS server
Write-Host "[4/6] Настройка KMS сервера..." -ForegroundColor Yellow

$kmsServers = @(
    "kms8.msguides.com",
    "kms.lotro.cc",
    "kms.chinancce.com",
    "kms.03k.org",
    "kms.digiboy.ir"
)

$kmsSet = $false
foreach ($server in $kmsServers) {
    try {
        Write-Host "  Пробую сервер: $server" -ForegroundColor Gray
        $result = cscript.exe //nologo "`"$osppPath`"" /sethst:$server 2>&1
        if ($result -match "successful|успешно|Successfully|successfully") {
            Write-Host "  [OK] KMS сервер установлен: $server" -ForegroundColor Green
            $kmsSet = $true
            Start-Sleep -Seconds 2
            break
        }
    } catch {
        # Continue
    }
}

if (-not $kmsSet) {
    Write-Host "  [WARN] Не удалось установить KMS сервер" -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Activate
Write-Host "[5/6] Активация Office..." -ForegroundColor Yellow

try {
    Write-Host "  Запускаю активацию..." -ForegroundColor Gray
    $result = cscript.exe //nologo "`"$osppPath`"" /act 2>&1
    
    Write-Host "  Результат:" -ForegroundColor Gray
    $result | Select-Object -First 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor White }
    
    if ($result -match "successful|успешно|Successfully|LICENSED") {
        Write-Host "  [OK] Активация выполнена!" -ForegroundColor Green
    }
} catch {
    Write-Host "  [ERROR] Ошибка: $_" -ForegroundColor Red
}

Write-Host ""

# Step 6: Final check
Write-Host "[6/6] Финальная проверка..." -ForegroundColor Yellow
Write-Host ""

try {
    $finalStatus = cscript.exe //nologo "`"$osppPath`"" /dstatus 2>&1
    Write-Host "Статус активации:" -ForegroundColor Cyan
    $finalStatus | Select-Object -First 25 | ForEach-Object { Write-Host $_ -ForegroundColor White }
    
    if ($finalStatus -match "LICENSE STATUS.*---LICENSED") {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Office успешно активирован!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "Активация может потребовать времени" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Следующие шаги:" -ForegroundColor Cyan
        Write-Host "1. Подождите 5-10 минут" -ForegroundColor White
        Write-Host "2. Перезапустите Office приложения" -ForegroundColor White
        Write-Host "3. Проверьте статус в Office:" -ForegroundColor White
        Write-Host "   Файл → Учетная запись → Информация о продукте" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Не удалось проверить финальный статус" -ForegroundColor Yellow
}

Write-Host ""
