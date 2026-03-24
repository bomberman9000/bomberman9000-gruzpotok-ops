# Скрипт очистки системы Windows

Write-Host "Очистка временных файлов..." -ForegroundColor Cyan

# Очистка временных файлов пользователя
$tempPaths = @(
    "$env:TEMP\*",
    "$env:LOCALAPPDATA\Temp\*",
    "$env:WINDIR\Temp\*"
)

foreach ($path in $tempPaths) {
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Очищено: $path" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠ Не удалось очистить: $path" -ForegroundColor Yellow
        }
    }
}

# Очистка корзины
Write-Host "Очистка корзины..." -ForegroundColor Cyan
Clear-RecycleBin -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Корзина очищена" -ForegroundColor Green

# Очистка кэша DNS
Write-Host "Очистка кэша DNS..." -ForegroundColor Cyan
ipconfig /flushdns | Out-Null
Write-Host "  ✓ Кэш DNS очищен" -ForegroundColor Green

# Очистка кэша Windows Store
Write-Host "Очистка кэша Windows Store..." -ForegroundColor Cyan
Get-AppxPackage -AllUsers | ForEach-Object {
    $package = $_.PackageFullName
    if ($package) {
        wsreset.exe | Out-Null
        Write-Host "  ✓ Кэш Windows Store очищен" -ForegroundColor Green
        break
    }
}

# Очистка логов Windows
Write-Host "Очистка логов Windows..." -ForegroundColor Cyan
wevtutil el | ForEach-Object {
    wevtutil cl "$_" 2>$null
}
Write-Host "  ✓ Логи очищены" -ForegroundColor Green

# Очистка кэша браузеров (опционально)
Write-Host ""
Write-Host "Очистка кэша браузеров..." -ForegroundColor Cyan
$browserPaths = @(
    "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache",
    "$env:APPDATA\Mozilla\Firefox\Profiles\*\cache2"
)

foreach ($path in $browserPaths) {
    if (Test-Path $path) {
        try {
            Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Очищен кэш браузера: $path" -ForegroundColor Green
        } catch {
            # Игнорируем ошибки (файлы могут быть заняты)
        }
    }
}

Write-Host ""
Write-Host "Очистка завершена!" -ForegroundColor Green


