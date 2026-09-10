@echo off
setlocal enabledelayedexpansion
title Private AI Cloud - Mission Launcher
echo ==============================================================
echo       PRIVATE AI CLOUD FOR ROBOTICS - LOCAL DEPLOYMENT
echo ==============================================================

cd /d "%~dp0"

:: Reset Redis host to local loopback to avoid DNS errors
set REDIS_HOST=127.0.0.1
set REDIS_PORT=6379

:: Step 1: Ensure Redis is Running
echo [*] Checking local Redis instance on port 6379...
powershell -Command "$t = New-Object Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1', 6379); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Redis is not active. Starting native Redis Server on port 6379...
    if exist "redis_bin\redis-server.exe" (
        start "Redis Server Daemon" "redis_bin\redis-server.exe"
        timeout /t 2 /nobreak >nul
    ) else if exist "..\redis_bin\redis-server.exe" (
        start "Redis Server Daemon" "..\redis_bin\redis-server.exe"
        timeout /t 2 /nobreak >nul
    ) else (
        echo [!] redis-server.exe not found in redis_bin.
    )
) else (
    echo [+] Redis is active on 127.0.0.1:6379.
)

:: Step 2: Virtual Environment
if not exist "venv\Scripts\activate.bat" (
    echo [*] Setting up virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: Step 3: Dependencies
echo [*] Checking dependencies...
pip install redis fastapi "uvicorn[standard]" python-jose pydantic requests Pillow pandas streamlit ultralytics

:: Step 4: Launch FastAPI Gateway
echo [+] Launching FastAPI Gateway on http://127.0.0.1:8000 ...
start "FastAPI Gateway" cmd /k "venv\Scripts\activate.bat && set REDIS_HOST=127.0.0.1 && uvicorn server:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul

:: Step 5: Launch AI Worker Daemon
echo [+] Launching YOLOv8 Inference Daemon...
start "AI Inference Daemon" cmd /k "venv\Scripts\activate.bat && set REDIS_HOST=127.0.0.1 && python worker.py"
timeout /t 2 /nobreak >nul

:: Step 6: Launch Streamlit Dashboard
echo [+] Launching Real-Time Monitoring Dashboard...
start "Mission Control Dashboard" cmd /k "venv\Scripts\activate.bat && set REDIS_HOST=127.0.0.1 && streamlit run dashboard.py"

echo ==============================================================
echo [SUCCESS] Private AI Cloud is operational!
echo --------------------------------------------------------------
echo - API Gateway:      http://127.0.0.1:8000
echo - Swagger Docs:     http://127.0.0.1:8000/docs
echo - Live Dashboard:   http://localhost:8501
echo.
echo To run the multi-robot concurrent stress simulation:
echo    python robot_simulator.py
echo ==============================================================
pause
