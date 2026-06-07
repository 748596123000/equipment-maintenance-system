@echo off
chcp 65001 >nul 2>&1
title 设备检修知识检索与作业系统

echo.
echo ========================================
echo   设备检修知识检索与作业系统
echo ========================================
echo.

cd /d "%~dp0"

REM ========== Node.js ==========
set "NODE_DIR=%~dp0.node\node-v22.16.0-win-x64"
if exist "%NODE_DIR%\node.exe" (
    set "PATH=%NODE_DIR%;%PATH%"
    echo [OK] Node.js: local
) else (
    where node >nul 2>&1
    if %errorlevel%==0 (
        echo [OK] Node.js: system
    ) else (
        echo [X] Node.js not found
        pause
        exit /b 1
    )
)

REM ========== Python ==========
set "PCMD="

if exist "%~dp0venv\Scripts\python.exe" (
    set "PCMD=%~dp0venv\Scripts\python.exe"
    echo [OK] Python: venv
    goto :pydone
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PCMD=%~dp0.venv\Scripts\python.exe"
    echo [OK] Python: .venv
    goto :pydone
)

if exist "C:\Users\zyj\.conda\envs\torch_gpu\python.exe" (
    set "PCMD=C:\Users\zyj\.conda\envs\torch_gpu\python.exe"
    echo [OK] Python: conda torch_gpu
    goto :pydone
)

where python >nul 2>&1
if %errorlevel%==0 (
    set "PCMD=python"
    echo [OK] Python: system
    goto :pydone
)

where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PCMD=python3"
    echo [OK] Python: system
    goto :pydone
)

echo [X] Python not found
pause
exit /b 1

:pydone
"%PCMD%" --version

REM ========== Project ==========
if not exist "app\main.py" (
    echo [X] app\main.py not found
    pause
    exit /b 1
)
echo [OK] Project

REM ========== Data dirs ==========
if not exist "data" mkdir data
if not exist "data\pdfs" mkdir data\pdfs
if not exist "data\images" mkdir data\images
if not exist "data\chroma_db" mkdir data\chroma_db

REM ========== Write launcher scripts ==========
echo @echo off > "%TEMP%\ems_backend.bat"
echo title Backend-FastAPI >> "%TEMP%\ems_backend.bat"
echo cd /d "%~dp0" >> "%TEMP%\ems_backend.bat"
echo set "PATH=%PATH%" >> "%TEMP%\ems_backend.bat"
echo "%PCMD%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> "%TEMP%\ems_backend.bat"

echo @echo off > "%TEMP%\ems_frontend.bat"
echo title Frontend-Vite >> "%TEMP%\ems_frontend.bat"
echo cd /d "%~dp0frontend" >> "%TEMP%\ems_frontend.bat"
echo set "PATH=%PATH%" >> "%TEMP%\ems_frontend.bat"
echo npm run dev >> "%TEMP%\ems_frontend.bat"

REM ========== Backend ==========
echo.
echo [1/2] Starting backend (port 8000)...
start "" "%TEMP%\ems_backend.bat"
ping -n 6 127.0.0.1 >nul

REM ========== Frontend ==========
echo [2/2] Starting frontend (port 3000)...
start "" "%TEMP%\ems_frontend.bat"

echo.
echo ========================================
echo   Started!
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000/docs
echo.
echo   Admin: admin / admin123
echo   User:   user / user123
echo.
echo   Press any key to open browser...
pause >nul

start http://localhost:3000
