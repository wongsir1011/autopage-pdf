@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AutoPage PDF v1.2.0

set "PYTHON_CMD="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3 was not found.
    echo Install Python 3.8 or later and enable Add Python to PATH.
    pause
    exit /b 1
)

if not exist "venv_win\Scripts\python.exe" (
    echo Creating the AutoPage PDF environment. Please wait...
    %PYTHON_CMD% -m venv "venv_win"
    if errorlevel 1 goto :error
)

if not exist "venv_win\.autopage_v1_2_0_ready" (
    echo Installing required packages. Internet access is needed this time...
    "venv_win\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    "venv_win\Scripts\python.exe" -m pip install -r "requirements.txt"
    if errorlevel 1 goto :error
    type nul > "venv_win\.autopage_v1_2_0_ready"
)

echo Starting AutoPage PDF v1.2.0...
start "" "venv_win\Scripts\pythonw.exe" "autopage_gui.py"
exit /b 0

:error
echo.
echo AutoPage PDF could not start. Review the error message above.
pause
exit /b 1
