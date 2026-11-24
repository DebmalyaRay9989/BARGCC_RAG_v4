@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0config\windows_paths.cmd" call "%~dp0config\windows_paths.cmd"
if not defined BARGCC_PYTHON set "BARGCC_PYTHON=%~d0\BARGCC_ENV\python.exe"
if not exist "%BARGCC_PYTHON%" (
 echo ERROR: Isolated Python not found: "%BARGCC_PYTHON%"
 echo Run 00_INSTALL_WINDOWS.cmd first.
 pause
 exit /b 2
)
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "BARG_REQUIRE_TOKEN=0"
set "BARG_ACCESS_TOKEN="
echo BARG-CC dashboard: http://127.0.0.1:7860/
echo Keep this window running. Press Ctrl+C to stop.
"%BARGCC_PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 7860 --workers 1
if errorlevel 1 (
 echo Server stopped with an error. Try 04_DIAGNOSE_WINDOWS.cmd
 pause
 exit /b 1
)
pause
