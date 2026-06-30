@echo off
setlocal

echo   TCAI v6 — Installer
echo   ====================
echo.

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

rem --- Check/Find Python ---
set "PYTHON=python"
set "PIP=pip"

rem Prefer bundled Python if available
if exist "%ROOT%\tools\python-venv\python.exe" (
    set "PYTHON=%ROOT%\tools\python-venv\python.exe"
    set "PIP=%ROOT%\tools\python-venv\python.exe -m pip"
)

echo   [1/3] Python: %PYTHON%
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FATAL] Python not found. Run tools\python-venv\python.exe directly.
    pause
    exit /b 1
)
echo.

echo   [2/3] Installing dependencies...
%PIP% install -e "%ROOT%" --quiet 2>&1
if %errorlevel% neq 0 (
    echo   [WARN] pip install failed. Try manually: %PIP% install -r requirements.txt
)
echo   Done.
echo.

echo   [3/3] Setting up config...
if not exist "%ROOT%\home" mkdir "%ROOT%\home"
if not exist "%ROOT%\home\.env" (
    copy "%ROOT%\.env.example" "%ROOT%\home\.env" >nul
    echo   Created home\.env from template.
    echo.
    echo   >>> EDIT home\.env and set your DEEPSEEK_API_KEY before running!
) else (
    echo   home\.env already exists (not overwritten).
)
echo.
echo   Install complete. Run: Start.bat
echo.
pause
