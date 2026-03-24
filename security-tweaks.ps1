# Скрипт настройки безопасности Windows

Write-Host "Настройка безопасности..." -ForegroundColor Cyan

# Включение брандмауэра Windows
Write-Host "Проверка брандмауэра..." -ForegroundColor Cyan
$firewall = Get-NetFirewallProfile
foreach ($profile in $firewall) {
    if ($profile.Enabled -eq $false) {
        Set-NetFirewallProfile -Profile $profile.Name -Enabled True
        Write-Host "  ✓ Брандмауэр включен для профиля: $($profile.Name)" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Брандмауэр уже включен: $($profile.Name)" -ForegroundColor Green
    }
}

# Настройка UAC (User Account Control)
Write-Host "Настройка UAC..." -ForegroundColor Cyan
$uacKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
if (-not (Test-Path $uacKey)) {
    New-Item -Path $uacKey -Force | Out-Null
}
Set-ItemProperty -Path $uacKey -Name "EnableLUA" -Value 1 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $uacKey -Name "ConsentPromptBehaviorAdmin" -Value 5 -ErrorAction SilentlyContinue
Write-Host "  ✓ UAC настроен" -ForegroundColor Green

# Отключение автозапуска с USB/CD
Write-Host "Отключение автозапуска..." -ForegroundColor Cyan
$autorunKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer"
if (-not (Test-Path $autorunKey)) {
    New-Item -Path $autorunKey -Force | Out-Null
}
Set-ItemProperty -Path $autorunKey -Name "NoDriveTypeAutoRun" -Value 255 -ErrorAction SilentlyContinue
Write-Host "  ✓ Автозапуск отключен" -ForegroundColor Green

# Настройка политики паролей
Write-Host "Проверка политики паролей..." -ForegroundColor Cyan
$passwordPolicy = Get-LocalUser | Where-Object { $_.PasswordRequired -eq $false }
if ($passwordPolicy) {
    Write-Host "  ⚠ Обнаружены пользователи без требования пароля" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Политика паролей в порядке" -ForegroundColor Green
}

# Отключение SMBv1 (устаревший и небезопасный)
Write-Host "Отключение SMBv1..." -ForegroundColor Cyan
$smb1 = Get-WindowsOptionalFeature -Online -FeatureName "SMB1Protocol" -ErrorAction SilentlyContinue
if ($smb1 -and $smb1.State -eq "Enabled") {
    Disable-WindowsOptionalFeature -Online -FeatureName "SMB1Protocol" -NoRestart -ErrorAction SilentlyContinue
    Write-Host "  ✓ SMBv1 отключен" -ForegroundColor Green
} else {
    Write-Host "  ✓ SMBv1 уже отключен" -ForegroundColor Green
}

# Настройка Windows Update
Write-Host "Проверка Windows Update..." -ForegroundColor Cyan
$updateService = Get-Service -Name "wuauserv" -ErrorAction SilentlyContinue
if ($updateService -and $updateService.Status -ne "Running") {
    Start-Service -Name "wuauserv" -ErrorAction SilentlyContinue
    Set-Service -Name "wuauserv" -StartupType Automatic -ErrorAction SilentlyContinue
    Write-Host "  ✓ Windows Update включен" -ForegroundColor Green
} else {
    Write-Host "  ✓ Windows Update работает" -ForegroundColor Green
}

# Отключение удаленного рабочего стола (если не используется)
Write-Host "Проверка удаленного рабочего стола..." -ForegroundColor Cyan
$rdpService = Get-Service -Name "TermService" -ErrorAction SilentlyContinue
if ($rdpService -and $rdpService.Status -eq "Running") {
    Write-Host "  ℹ Удаленный рабочий стол включен" -ForegroundColor Yellow
    Write-Host "  ℹ Если не используете, отключите вручную в настройках системы" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Удаленный рабочий стол отключен" -ForegroundColor Green
}

# Настройка защиты от эксплойтов
Write-Host "Настройка защиты от эксплойтов..." -ForegroundColor Cyan
$exploitProtection = @{
    "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" = @{
        "FeatureSettingsOverride" = 0
        "FeatureSettingsOverrideMask" = 3
    }
}

foreach ($regPath in $exploitProtection.Keys) {
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    foreach ($key in $exploitProtection[$regPath].Keys) {
        Set-ItemProperty -Path $regPath -Name $key -Value $exploitProtection[$regPath][$key] -ErrorAction SilentlyContinue
    }
}
Write-Host "  ✓ Защита от эксплойтов настроена" -ForegroundColor Green

# Отключение ненужных сетевых протоколов
Write-Host "Оптимизация сетевых протоколов..." -ForegroundColor Cyan
$networkFeatures = @(
    "SMB1Protocol",
    "WorkFolders-Client"
)

foreach ($feature in $networkFeatures) {
    $featureState = Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction SilentlyContinue
    if ($featureState -and $featureState.State -eq "Enabled") {
        Disable-WindowsOptionalFeature -Online -FeatureName $feature -NoRestart -ErrorAction SilentlyContinue
        Write-Host "  ✓ Отключен: $feature" -ForegroundColor Green
    }
}

# Настройка SmartScreen
Write-Host "Проверка SmartScreen..." -ForegroundColor Cyan
$smartscreenKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer"
if (-not (Test-Path $smartscreenKey)) {
    New-Item -Path $smartscreenKey -Force | Out-Null
}
Set-ItemProperty -Path $smartscreenKey -Name "SmartScreenEnabled" -Value "RequireAdmin" -ErrorAction SilentlyContinue
Write-Host "  ✓ SmartScreen настроен" -ForegroundColor Green

Write-Host ""
Write-Host "Настройка безопасности завершена!" -ForegroundColor Green

