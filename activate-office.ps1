# Activate Microsoft Office
# Run as Administrator!

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Активация Microsoft Office" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] Требуются права администратора!" -ForegroundColor Red
    Write-Host "[INFO] Запустите PowerShell от имени администратора" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# Step 1: Find Office installation
Write-Host "[1/5] Поиск установки Office..." -ForegroundColor Yellow

$officePaths = @(
    "C:\Program Files\Microsoft Office",
    "C:\Program Files (x86)\Microsoft Office"
)

$officeFound = $false
$officeVersion = $null
$osppPath = $null

foreach ($path in $officePaths) {
    if (Test-Path $path) {
        $versions = Get-ChildItem $path -Directory -ErrorAction SilentlyContinue
        foreach ($version in $versions) {
            $ospp = Join-Path $version.FullName "Office16\OSPP.VBS"
            if (Test-Path $ospp) {
                $officeFound = $true
                $officeVersion = $version.Name
                $osppPath = $ospp
                Write-Host "  [OK] Найден Office: $($version.FullName)" -ForegroundColor Green
                break
            }
        }
        if ($officeFound) { break }
    }
}

if (-not $officeFound) {
    Write-Host "  [ERROR] Office не найден!" -ForegroundColor Red
    Write-Host "  [INFO] Убедитесь, что Office установлен" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""

# Step 2: Check current activation status
Write-Host "[2/5] Проверка текущего статуса активации..." -ForegroundColor Yellow

try {
    $status = cscript.exe //nologo "`"$osppPath`"" /dstatus 2>&1
    Write-Host "  Текущий статус:" -ForegroundColor Gray
    $status | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} catch {
    Write-Host "  [WARN] Не удалось проверить статус" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: Install KMS key (if needed)
Write-Host "[3/5] Установка KMS ключа..." -ForegroundColor Yellow

# KMS keys for Office 2021/2019/2016
$kmsKeys = @{
    "Office 2021 ProPlus" = "FXYTK-NJJ8C-GB6DW-3DYQT-6F7TH"
    "Office 2021 Standard" = "KDX7X-BNVR8-TXXGX-4Q7Y8-78VT3"
    "Office 2019 ProPlus" = "NMMKJ-6RK4F-KMJVX-8D9MJ-6MWKP"
    "Office 2019 Standard" = "6NWWJ-YQWMR-QKGCB-6TMB3-9D9HK"
    "Office 2016 ProPlus" = "XQNVK-8JYDB-WJ9W3-YJ8YR-WFG99"
    "Office 2016 Standard" = "JNRGM-WHDWX-FJJG3-K47QV-DRTFM"
}

Write-Host "  Пробую установить KMS ключи..." -ForegroundColor Gray

$keyInstalled = $false
foreach ($key in $kmsKeys.Values) {
    try {
        $result = cscript.exe //nologo "`"$osppPath`"" /inpkey:$key 2>&1
        if ($result -match "successful|успешно") {
            Write-Host "  [OK] Ключ установлен: $key" -ForegroundColor Green
            $keyInstalled = $true
            break
        }
    } catch {
        # Continue to next key
    }
}

if (-not $keyInstalled) {
    Write-Host "  [WARN] Не удалось установить KMS ключ автоматически" -ForegroundColor Yellow
    Write-Host "  [INFO] Попробуем активировать с существующим ключом" -ForegroundColor Gray
}

Write-Host ""

# Step 4: Set KMS server
Write-Host "[4/5] Настройка KMS сервера..." -ForegroundColor Yellow

# Common KMS servers
$kmsServers = @(
    "kms8.msguides.com",
    "kms.lotro.cc",
    "kms.chinancce.com",
    "kms.03k.org"
)

$kmsSet = $false
foreach ($server in $kmsServers) {
    try {
        Write-Host "  Пробую: $server" -ForegroundColor Gray
        $result = cscript.exe //nologo "`"$osppPath`"" /sethst:$server 2>&1
        if ($result -match "successful|успешно|Successfully") {
            Write-Host "  [OK] KMS сервер установлен: $server" -ForegroundColor Green
            $kmsSet = $true
            break
        }
    } catch {
        # Continue to next server
    }
}

if (-not $kmsSet) {
    Write-Host "  [WARN] Не удалось установить KMS сервер автоматически" -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Activate Office
Write-Host "[5/5] Активация Office..." -ForegroundColor Yellow

try {
    Write-Host "  Запускаю активацию..." -ForegroundColor Gray
    $result = cscript.exe //nologo "`"$osppPath`"" /act 2>&1
    
    Write-Host "  Результат:" -ForegroundColor Gray
    $result | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    
    if ($result -match "successful|успешно|Successfully|LICENSE STATUS.*---LICENSED") {
        Write-Host "  [OK] Office активирован!" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Активация может не завершиться автоматически" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Ошибка при активации: $_" -ForegroundColor Red
}

Write-Host ""

# Final status check
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Проверка финального статуса..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    $finalStatus = cscript.exe //nologo "`"$osppPath`"" /dstatus 2>&1
    $finalStatus | ForEach-Object { Write-Host $_ -ForegroundColor White }
    
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
        Write-Host "Если Office не активирован:" -ForegroundColor Cyan
        Write-Host "1. Подождите несколько минут" -ForegroundColor White
        Write-Host "2. Перезапустите Office приложения" -ForegroundColor White
        Write-Host "3. Попробуйте выполнить команду вручную:" -ForegroundColor White
        Write-Host "   cscript `"$osppPath`" /act" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [WARN] Не удалось проверить финальный статус" -ForegroundColor Yellow
}

Write-Host ""

pause

