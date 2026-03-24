# Автоматический запуск настройки с правами администратора
# Если прав нет - откроет новое окно с правами

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "`n[INFO] Требуются права администратора..." -ForegroundColor Yellow
    Write-Host "[INFO] Открываю новое окно PowerShell с правами администратора...`n" -ForegroundColor Cyan
    
    $scriptPath = Join-Path $PSScriptRoot "windows11-sysadmin-setup.ps1"
    
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$scriptPath`""
    
    Write-Host "[OK] Новое окно открыто!`n" -ForegroundColor Green
    Write-Host "Продолжайте настройку в новом окне.`n" -ForegroundColor Gray
    
    exit
}

# Если права уже есть - запускаем напрямую
& "$PSScriptRoot\windows11-sysadmin-setup.ps1"
