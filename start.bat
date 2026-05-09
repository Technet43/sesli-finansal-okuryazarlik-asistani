@echo off
REM KAP Okuryazar - cift tikla baslatici
REM PowerShell scriptini ExecutionPolicy bypass ile calistirir.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
    echo.
    echo Bir hata olustu. Yukaridaki mesajlari oku.
    pause
)
