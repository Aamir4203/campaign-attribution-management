@echo off
REM CAM Project Deployment Script for Windows
REM Starts both frontend and backend services

setlocal enabledelayedexpansion

echo 🚀 Starting CAM (Campaign Attribution Management) Deployment...

REM Get script directory
set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "VENV_DIR=%PROJECT_ROOT%\CAM_Env"
set "LOGS_DIR=%PROJECT_ROOT%\logs"

REM Configuration
set BACKEND_PORT=5000
set FRONTEND_PORT=5173

REM Create logs directory
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

REM Function to check if port is in use (Windows)
echo 🔍 Checking for existing services...

REM Kill existing processes on ports
echo ⚠️  Stopping any existing CAM services...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%BACKEND_PORT%"') do (
    if not "%%i"=="0" (
        echo Killing process %%i on port %BACKEND_PORT%
        taskkill /PID %%i /F >nul 2>&1
    )
)

for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%FRONTEND_PORT%"') do (
    if not "%%i"=="0" (
        echo Killing process %%i on port %FRONTEND_PORT%
        taskkill /PID %%i /F >nul 2>&1
    )
)

REM Start Backend
echo 🔧 Starting Backend Service...

REM Check if virtual environment exists
if not exist "%VENV_DIR%" (
    echo ❌ Virtual environment not found at %VENV_DIR%
    echo 📝 Please run: python -m venv CAM_Env
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"

REM Activate virtual environment and start backend
echo 🐍 Activating Python virtual environment...
call "%VENV_DIR%\Scripts\Activate.ps1"

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing Python dependencies...
    pip install -r requirements.txt
)

echo ✅ Starting Flask API on port %BACKEND_PORT%...
start "CAM Backend" /min cmd /c "python simple_api.py > \"%LOGS_DIR%\backend.log\" 2>&1"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend
echo 🎨 Starting Frontend Service...
cd /d "%FRONTEND_DIR%"

REM Check if node_modules exists
if not exist "node_modules" (
    echo 📦 Installing Node.js dependencies...
    call npm install
)

echo ✅ Starting Vite dev server on port %FRONTEND_PORT%...
start "CAM Frontend" /min cmd /c "npm run dev > \"%LOGS_DIR%\frontend.log\" 2>&1"

REM Wait for frontend to start
timeout /t 5 /nobreak >nul

REM Display status
echo.
echo 🎉 CAM Deployment Complete!
echo.
echo 📋 Service Status:
echo   🔧 Backend API:  http://localhost:%BACKEND_PORT%
echo   🎨 Frontend UI:  http://localhost:%FRONTEND_PORT%
echo.
echo 📝 Logs Location: %LOGS_DIR%
echo   Backend:  logs\backend.log
echo   Frontend: logs\frontend.log
echo.
echo 🛑 To stop services: stop-cam.bat
echo.
echo ✨ Ready for testing!
echo.

REM Open browser to frontend
timeout /t 2 /nobreak >nul
start http://localhost:%FRONTEND_PORT%

pause
