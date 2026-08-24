@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title AutoPage PDF v1.2.0 - 啟動中...

where python >nul 2>nul
if errorlevel 1 (
    echo 找不到 Python。請先安裝 Python 3.8 或以上版本，並勾選 Add Python to PATH。
    pause
    exit /b 1
)

if not exist "venv_win\Scripts\python.exe" (
    echo [首次執行] 正在建立獨立執行環境，請稍候...
    python -m venv venv_win
    if errorlevel 1 goto :error
)

call venv_win\Scripts\activate.bat
if not exist "venv_win\.autopage_v1_2_0_ready" (
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 goto :error
    type nul > "venv_win\.autopage_v1_2_0_ready"
)

start "" venv_win\Scripts\pythonw.exe autopage_gui.py
exit /b 0

:error
echo.
echo 啟動失敗，請檢查上方錯誤訊息。
pause
exit /b 1
