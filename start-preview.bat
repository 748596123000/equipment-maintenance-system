@echo off
cd /d "%~dp0frontend"
echo ========================================
echo   设备检修知识系统 - 预览模式
echo ========================================
echo.
echo Starting preview server...
echo Access the site at: http://localhost:3001
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.
npm run preview -- --port 3001 --host
pause