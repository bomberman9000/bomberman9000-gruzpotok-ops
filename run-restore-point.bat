@echo off
chcp 65001 >nul
echo ========================================
echo   Создание точки восстановления
echo ========================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0create-restore-point.ps1\"' -Verb RunAs -Wait"

pause

