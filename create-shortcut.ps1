$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$PWD\Оптимизация Windows.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PWD\optimize-windows.ps1`" -All"
$Shortcut.WorkingDirectory = $PWD.Path
$Shortcut.Description = "Оптимизация Windows - запуск с правами администратора"
$Shortcut.Save()

# Устанавливаем "Запуск от имени администратора" через реестр
$bytes = [System.IO.File]::ReadAllBytes("$PWD\Оптимизация Windows.lnk")
$bytes[0x15] = $bytes[0x15] -bor 0x20
[System.IO.File]::WriteAllBytes("$PWD\Оптимизация Windows.lnk", $bytes)

Write-Host "Shortcut created: Optimizaciya Windows.lnk" -ForegroundColor Green
Write-Host "Double-click to run!" -ForegroundColor Yellow

