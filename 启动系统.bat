@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d C:\Users\张可心\fund-advisory-system

echo.
echo ============================================================
echo   基金投资顾问系统
echo ============================================================
echo.
echo   本机访问: http://localhost:8504
echo.

REM Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%
echo   手机访问: http://%LOCAL_IP%:8504（需连同一WiFi）
echo.
echo   关掉此窗口 = 停止系统
echo ============================================================
echo.
D:\python\python.exe -m streamlit run dashboard\app.py --server.headless true --browser.gatherUsageStats false --server.port 8504 --server.address 0.0.0.0
pause
