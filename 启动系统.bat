@echo off
chcp 65001 >nul 2>&1
title Equipment System

echo ========================================
echo   Equipment Maintenance System
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [OK] Python found

REM Check frontend directory
if not exist "frontend" (
    echo [ERROR] frontend folder not found
    pause
    exit /b 1
)

echo [OK] Directory check passed

REM Start backend
echo [1/2] Starting backend service...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
start "Backend" cmd /k "cd /d %~dp0 && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\deactivate.bat 2>nul
)

timeout /t 3 /nobreak >nul

REM Start frontend
echo [2/2] Starting frontend service...
start "Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================
echo   Startup Complete!
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   API:      http://localhost:8000/docs
echo.
echo   Admin: admin / admin123
echo   User:  user / user123
echo.
echo   Press any key to open browser...
pause >nul

start http://localhost:3000