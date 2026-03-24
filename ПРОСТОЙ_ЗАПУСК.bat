@echo off
title Оптимизация Windows
color 0B

echo.
echo ========================================
echo    ЗАПУСК ОПТИМИЗАЦИИ WINDOWS
echo ========================================
echo.
echo Нажмите любую клавишу для запуска...
echo (Подтвердите запрос UAC - нажмите Да)
echo.
pause >nul

cd /d "%~dp0"

:: Используем VBScript для запроса прав администратора
cscript //nologo //E:VBScript "%~dp0Запустить.vbs"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo ОШИБКА при запуске!
    echo ========================================
    echo.
    echo Попробуйте вручную:
    echo 1. Правой кнопкой на файл optimize-windows.ps1
    echo 2. Выберите "Запустить с PowerShell"
    echo 3. В открывшемся окне выполните: .\optimize-windows.ps1 -All
    echo.
)

timeout /t 3 >nul

