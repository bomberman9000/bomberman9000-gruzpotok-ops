# Скрипт для установки красивых обоев
# Можно добавить свои обои в папку wallpapers

Write-Host "Установка красивых обоев..." -ForegroundColor Cyan
Write-Host ""

$wallpapersFolder = Join-Path $PSScriptRoot "wallpapers"
$wallpaperPath = $null

# Проверяем наличие папки с обоями
if (Test-Path $wallpapersFolder) {
    $wallpapers = Get-ChildItem -Path $wallpapersFolder -Include *.jpg,*.jpeg,*.png,*.bmp -Recurse | Where-Object { -not $_.PSIsContainer }
    
    if ($wallpapers.Count -gt 0) {
        # Выбираем случайные обои или первые найденные
        $wallpaperPath = $wallpapers[0].FullName
        Write-Host "Найдены обои в папке wallpapers" -ForegroundColor Green
    }
}

if ($wallpaperPath -and (Test-Path $wallpaperPath)) {
    try {
        # Устанавливаем обои
        Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class Wallpaper {
            [DllImport("user32.dll", CharSet=CharSet.Auto)]
            public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
            public static void SetWallpaper(string path) {
                SystemParametersInfo(20, 0, path, 3);
            }
        }
"@
        [Wallpaper]::SetWallpaper($wallpaperPath)
        Write-Host "  ✓ Обои установлены: $wallpaperPath" -ForegroundColor Green
        
        # Настраиваем стиль обоев (растянуть)
        $wallpaperKey = "HKCU:\Control Panel\Desktop"
        Set-ItemProperty -Path $wallpaperKey -Name "WallpaperStyle" -Value "10" -ErrorAction SilentlyContinue
        Set-ItemProperty -Path $wallpaperKey -Name "TileWallpaper" -Value "0" -ErrorAction SilentlyContinue
        
    } catch {
        Write-Host "  ⚠ Не удалось установить обои автоматически" -ForegroundColor Yellow
        Write-Host "  Установите обои вручную: ПКМ на файле → Установить как фоновый рисунок" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ℹ Папка 'wallpapers' не найдена или пуста" -ForegroundColor Yellow
    Write-Host "  Создайте папку 'wallpapers' и добавьте туда свои обои (jpg, png, bmp)" -ForegroundColor Yellow
    Write-Host "  Затем запустите этот скрипт снова" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Готово!" -ForegroundColor Green





