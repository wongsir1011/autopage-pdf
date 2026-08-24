@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title AutoPage PDF v1.2.0 打包工具

where python >nul 2>nul
if errorlevel 1 (
    echo 找不到 Python。請先安裝 Python 3.8 或以上版本。
    pause
    exit /b 1
)

if not exist "venv_win\Scripts\python.exe" (
    python -m venv venv_win
    if errorlevel 1 goto :error
)

call venv_win\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

pyinstaller --onefile --windowed --name "AutoPage_PDF_v1.2.0" --clean autopage_gui.py
if errorlevel 1 goto :error

echo.
echo 打包完成：dist\AutoPage_PDF_v1.2.0.exe
pause
exit /b 0

:error
echo.
echo 打包失敗，請檢查上方錯誤訊息。
pause
exit /b 1
