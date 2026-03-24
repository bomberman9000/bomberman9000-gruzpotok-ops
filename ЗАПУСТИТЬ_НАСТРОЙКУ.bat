@echo off
chcp 65001 >nul
color 0B

echo.
echo ════════════════════════════════════════
echo   WINDOWS 11 - НАСТРОЙКА СИСАДМИНА
echo ════════════════════════════════════════
echo.
echo Этот скрипт запустит профессиональную
echo настройку системы Windows 11
echo.
echo ЧТО БУДЕТ СДЕЛАНО:
echo   ✓ Оптимизация производительности
echo   ✓ Настройка проводника
echo   ✓ Отключение телеметрии
echo   ✓ Настройка безопасности
echo   ✓ Оптимизация сети
echo   ✓ Очистка системы
echo.
echo ════════════════════════════════════════
echo.
echo ВНИМАНИЕ: Нужны права администратора!
echo.
pause

REM Проверка прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [ОШИБКА] Нужны права администратора!
    echo.
    echo Запустите этот файл от имени администратора:
    echo   Правый клик → Запуск от имени администратора
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Права администратора получены
echo.
echo Запуск настройки...
echo.

REM Запуск PowerShell скрипта
powershell -ExecutionPolicy Bypass -File "%~dp0windows11-sysadmin-setup.ps1"

if %errorlevel% equ 0 (
    echo.
    echo ════════════════════════════════════════
    echo   НАСТРОЙКА ЗАВЕРШЕНА!
    echo ════════════════════════════════════════
    echo.
    echo Следующий шаг:
    echo   1. Запустите: install-essential-programs.ps1
    echo   2. Или: УСТАНОВИТЬ_ПРОГРАММЫ.bat
    echo.
    echo Для применения всех изменений
    echo ПЕРЕЗАГРУЗИТЕ КОМПЬЮТЕР!
    echo.
) else (
    echo.
    echo [ОШИБКА] Произошла ошибка при настройке
    echo.
)

pause
