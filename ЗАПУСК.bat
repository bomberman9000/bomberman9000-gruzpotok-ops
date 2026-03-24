@echo off
chcp 65001 >nul
title Оптимизация Windows
color 0A

echo.
echo ========================================
echo    ОПТИМИЗАЦИЯ WINDOWS
echo ========================================
echo.
echo Этот скрипт выполнит:
echo   - Очистку системы
echo   - Оптимизацию производительности  
echo   - Настройку безопасности
echo.
echo ВАЖНО: Требуются права администратора!
echo.
pause

cd /d "%~dp0"

echo.
echo Запуск PowerShell с правами администратора...
echo Подтвердите запрос UAC (нажмите Да)
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0optimize-windows.ps1\" -All' -Verb RunAs -Wait"

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo Оптимизация завершена!
) else (
    echo Произошла ошибка при выполнении.
    echo.
    echo Попробуйте запустить вручную:
    echo   1. Откройте PowerShell от имени администратора
    echo   2. Перейдите: cd "%CD%"
    echo   3. Запустите: .\optimize-windows.ps1 -All
)
echo ========================================
echo.
pause

