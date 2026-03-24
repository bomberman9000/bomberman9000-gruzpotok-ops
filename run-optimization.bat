@echo off
chcp 65001 >nul
cls
echo ========================================
echo   Оптимизация Windows
echo ========================================
echo.
echo Запуск с правами администратора...
echo.
echo Подтвердите запрос UAC (нажмите Да)
echo.

cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& {Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0optimize-windows.ps1\" -All' -Verb RunAs -Wait}"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ОШИБКА: Не удалось запустить скрипт!
    echo Попробуйте запустить вручную:
    echo   1. Правой кнопкой на optimize-windows.ps1
    echo   2. Выберите "Запустить с PowerShell"
    echo   3. В PowerShell выполните: .\optimize-windows.ps1 -All
    echo.
)

pause

