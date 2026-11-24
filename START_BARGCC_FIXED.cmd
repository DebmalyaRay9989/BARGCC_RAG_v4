
@echo off
setlocal
title BARG-CC Agentic RAG Research Studio v4
cd /d "%~dp0"

echo ============================================
echo  BARG-CC RAG RESEARCH STUDIO v4.0.0
echo ============================================
echo.
echo Server: http://127.0.0.1:7861/
echo JavaScript MIME correction: ENABLED
echo Press CTRL+C to stop the server.
echo.

set "PYTHON_EXE=python"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" -c "import mimetypes; mimetypes.init(); mimetypes.add_type('text/javascript', '.js'); mimetypes.add_type('text/css', '.css'); import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port=7861, use_colors=False)"

echo.
echo Server stopped.
pause
endlocal
