@echo off
setlocal
title GES Saatlik Uretim Tahmin Motoru

rem Always run relative to this file, even when it is double-clicked elsewhere.
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src"
set "PYTHON_EXE=C:\Users\Staj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python calisma ortami bulunamadi:
    echo %PYTHON_EXE%
    echo README.md dosyasindaki kurulum adimlarini uygulayin.
    pause
    exit /b 1
)

echo GES Tahmin Motoru baslatiliyor...
start "GES Tahmin Motoru" /min "%PYTHON_EXE%" -m ges_forecast --host 127.0.0.1 --port 8080 --data-dir data

rem Give the local web server a moment to start, then open it in the default browser.
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8080/"

endlocal
