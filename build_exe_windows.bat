@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AutoPage PDF v1.3.0 Builder

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
    echo Creating the build environment. Please wait...
    %PYTHON_CMD% -m venv "venv_win"
    if errorlevel 1 goto :error
)

"venv_win\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
"venv_win\Scripts\python.exe" -m pip install -r "requirements-dev.txt"
if errorlevel 1 goto :error

"venv_win\Scripts\python.exe" -m PyInstaller --onefile --windowed --name "AutoPage_PDF_v1.3.0" --clean "autopage_gui.py"
if errorlevel 1 goto :error

echo.
echo Build completed: dist\AutoPage_PDF_v1.3.0.exe
pause
exit /b 0

:error
echo.
echo Build failed. Review the error message above.
pause
exit /b 1
