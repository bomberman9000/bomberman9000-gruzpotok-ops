@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   ОТКРЫТИЕ NVIDIA CONTROL PANEL
echo ========================================
echo.

REM Попытка открыть через разные пути
echo Открываю NVIDIA Control Panel...
echo.

start "" nvcpl.cpl 2>nul

if %errorlevel% neq 0 (
    echo Попытка через альтернативный путь...
    start "" "C:\Program Files\NVIDIA Corporation\Control Panel Client\nvcpl.cpl" 2>nul
)

if %errorlevel% neq 0 (
    echo Попытка через shell...
    start "" shell:::{ED228FDF-9EA8-4870-83b1-96b02CFE0D52} 2>nul
)

timeout /t 2 >nul

echo.
echo ========================================
echo   ЧТО НАСТРОИТЬ:
echo ========================================
echo.
echo 1. Управление параметрами 3D:
echo    → Высокое качество
echo    → Сглаживание: Включить
echo.
echo 2. Изменение разрешения:
echo    → 3840x2160 (4K)
echo    → 32-bit цвет
echo    → Максимальная частота
echo.
echo 3. Регулировка цвета:
echo    → Использовать настройки NVIDIA
echo    → Яркость/Контраст: 50%%
echo.
echo ========================================
echo.
