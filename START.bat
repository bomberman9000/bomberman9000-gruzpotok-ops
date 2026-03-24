@echo off
chcp 65001 >nul
title Оптимизация Windows
color 0A
cls

echo.
echo ========================================
echo    ОПТИМИЗАЦИЯ WINDOWS
echo ========================================
echo.
echo Сейчас откроется PowerShell с правами администратора
echo Подтвердите запрос UAC (нажмите ДА)
echo.
echo Нажмите любую клавишу для продолжения...
pause >nul

cd /d "%~dp0"

:: Прямой запуск через PowerShell с запросом прав
powershell.exe -Command "if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0optimize-windows.ps1\" -All' -Verb RunAs } else { & '%~dp0optimize-windows.ps1' -All }"

echo.
echo ========================================
echo Готово!
echo ========================================
echo.
pause

