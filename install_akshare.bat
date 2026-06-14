@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo Installing akshare with UTF-8 encoding...
D:\python\python.exe -m pip install akshare --no-cache-dir
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   akshare installed successfully!
    echo ========================================
) else (
    echo.
    echo Installation failed. Trying alternative method...
    D:\python\python.exe -m pip install akshare --no-cache-dir --force-reinstall
)
pause
