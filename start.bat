@echo off
chcp 65001 >nul
echo ============================================================
echo   设备检修知识检索与作业系统 - Windows启动脚本
echo ============================================================
echo.

cd /d "%~dp0"

if not exist .env (
    echo [错误] 未找到.env文件，请先复制.env.example为.env并配置API Key
    echo   copy .env.example .env
    pause
    exit /b 1
)

echo [1/2] 启动FastAPI后端 (端口8000)...
start "FastAPI后端" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo [2/2] 启动Streamlit前端 (端口8501)...
start "Streamlit前端" cmd /k "streamlit run ui/app.py --server.port 8501 --server.headless true"

echo.
echo ============================================================
echo   系统已启动！
echo   前端: http://localhost:8501
echo   API:  http://localhost:8000/docs
echo ============================================================
echo.
echo 关闭此窗口不会停止服务，请关闭对应的命令行窗口来停止
pause