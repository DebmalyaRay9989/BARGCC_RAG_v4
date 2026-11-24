@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\doctor_windows.ps1" -AppDir "%~dp0"
pause
