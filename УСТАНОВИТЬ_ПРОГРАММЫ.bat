@echo off
chcp 65001 >nul
color 0A

echo.
echo ════════════════════════════════════════
echo   УСТАНОВКА НЕОБХОДИМЫХ ПРОГРАММ
echo ════════════════════════════════════════
echo.
echo Будет использован winget (встроенный в Windows 11)
echo.
echo ДОСТУПНЫ ДЛЯ УСТАНОВКИ:
echo.
echo ОСНОВНЫЕ:
echo   • Браузеры (Chrome, Firefox)
echo   • Редакторы (VSCode, Notepad++)
echo   • Архиваторы (7-Zip)
echo   • Медиаплееры (VLC)
echo   • Мессенджеры (Telegram, Discord)
echo   • Утилиты (Everything, ShareX)
echo   • Разработка (Git, Python, PowerShell 7)
echo.
echo УТИЛИТЫ:
echo   • CPU-Z, GPU-Z, HWiNFO
echo   • MSI Afterburner
echo   • CrystalDiskInfo
echo.
echo ════════════════════════════════════════
echo.
echo Вам будет предложен выбор:
echo   [A] Всё основное
echo   [B] Всё (основное + утилиты)
echo   [C] Выборочная установка
echo   [N] Ничего не устанавливать
echo.
pause

echo.
echo Запуск установщика...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0install-essential-programs.ps1"

echo.
echo ════════════════════════════════════════
echo   УСТАНОВКА ЗАВЕРШЕНА
echo ════════════════════════════════════════
echo.
echo Рекомендация: Перезагрузите компьютер
echo.
pause
