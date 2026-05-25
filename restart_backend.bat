@echo off
echo ========================================
echo 重启后端服务
echo ========================================

echo [1/3] 停止当前服务...
taskkill /F /IM python.exe 2>nul

echo [2/3] 等待服务完全停止...
timeout /t 3 /nobreak >nul

echo [3/3] 启动新服务...
start "Backend Server" cmd /k "cd /d D:\Chinese team\equipment-maintenance-system-v2-fixed && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

echo 服务已重启，等待启动...
timeout /t 5 /nobreak >nul

echo 检查服务状态...
curl -s http://localhost:8001/health

echo ========================================
echo 重启完成！
echo ========================================
pause
