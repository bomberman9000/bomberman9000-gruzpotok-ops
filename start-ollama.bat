@echo off
REM Simple batch file to start Ollama
REM This file is safe and won't trigger antivirus

cd /d "C:\Users\Shata\AppData\Local\Programs\Ollama"
start "" ollama.exe
timeout /t 2 /nobreak >nul

REM Check if started
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Ollama started successfully
) else (
    echo Ollama may not have started
)






