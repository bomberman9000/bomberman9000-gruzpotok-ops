@echo off
chcp 65001 >nul
echo Setting up Ollama autostart...
echo.

set "OLLAMA_PATH=C:\Users\Shata\AppData\Local\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_PATH%" (
    echo ERROR: Ollama not found!
    pause
    exit /b 1
)

echo Found Ollama: %OLLAMA_PATH%
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
echo Startup folder: %STARTUP_FOLDER%
echo.

REM Create VBS script to create shortcut (more reliable than PowerShell)
set "VBS_SCRIPT=%TEMP%\create_shortcut.vbs"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%STARTUP_FOLDER%\Ollama.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%OLLAMA_PATH%"
echo oLink.WorkingDirectory = "%~dp0"
echo oLink.Description = "Start Ollama on login"
echo oLink.Save
) > "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

if exist "%STARTUP_FOLDER%\Ollama.lnk" (
    echo.
    echo SUCCESS: Autostart configured!
    echo Ollama will start automatically when you log in.
    echo.
    echo To test: Log out (Win + L) and log in again
) else (
    echo.
    echo ERROR: Could not create shortcut
)

echo.
pause





