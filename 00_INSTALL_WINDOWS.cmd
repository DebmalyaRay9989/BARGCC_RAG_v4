@echo off
setlocal
chcp 65001 >nul 2>&1
color 0B
echo ========================================================
echo BARG-CC Agentic RAG v4 - Complete Windows Installation
echo ========================================================
echo This installer uses Miniconda, not the 'py' command.
echo It copies the application to a short Windows path.
echo Your existing research folders will not be deleted.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install_windows.ps1" -SourceDir "%~dp0" -Launch
set "INSTALL_RESULT=%ERRORLEVEL%"
echo.
if not "%INSTALL_RESULT%"=="0" (
 echo Installation or startup failed. Review the output above.
 echo See docs\WINDOWS_TROUBLESHOOTING.md
) else (
 echo Application process stopped normally.
)
echo.
pause
exit /b %INSTALL_RESULT%
