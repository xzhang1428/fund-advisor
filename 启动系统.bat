@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d C:\Users\张可心\fund-advisory-system
echo.
echo ============================================================
echo   基金投资顾问系统 - 启动中...
echo ============================================================
echo.
echo   本地访问: http://localhost:8504
echo   手机/平板: http://192.168.2.55:8504
echo.
echo   关闭此窗口即停止系统
echo ============================================================
echo.
D:\python\python.exe -m streamlit run dashboard\app.py --server.headless true --browser.gatherUsageStats false --server.port 8504 --server.address 0.0.0.0
pause
