@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0config\windows_paths.cmd" call "%~dp0config\windows_paths.cmd"
if not defined BARGCC_PYTHON set "BARGCC_PYTHON=%~d0\BARGCC_ENV\python.exe"
if not exist "%BARGCC_PYTHON%" (
 echo Python missing. Run 00_INSTALL_WINDOWS.cmd
 pause
 exit /b 2
)
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
"%BARGCC_PYTHON%" -m pytest -q tests
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
