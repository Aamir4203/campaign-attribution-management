@echo off
REM CAM Project Stop Script for Windows
REM Stops both frontend and backend services

echo 🛑 Stopping CAM Services...

REM Configuration
set BACKEND_PORT=5000
set FRONTEND_PORT=5173

REM Kill processes on Backend port
echo 🔄 Stopping Backend services on port %BACKEND_PORT%...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%BACKEND_PORT%"') do (
    if not "%%i"=="0" (
        echo Stopping Backend process %%i
        taskkill /PID %%i /F >nul 2>&1
    )
)

REM Kill processes on Frontend port
echo 🔄 Stopping Frontend services on port %FRONTEND_PORT%...
for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%FRONTEND_PORT%"') do (
    if not "%%i"=="0" (
        echo Stopping Frontend process %%i
        taskkill /PID %%i /F >nul 2>&1
    )
)

REM Kill any remaining CAM processes
echo 🧹 Cleaning up remaining processes...
taskkill /FI "WINDOWTITLE eq CAM Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq CAM Frontend*" /F >nul 2>&1

REM Kill Node.js processes (Vite)
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq node.exe" /FO CSV ^| findstr "node.exe"') do (
    set pid=%%i
    set pid=!pid:"=!
    for /f "tokens=*" %%j in ('wmic process where "ProcessId=!pid!" get CommandLine /value ^| findstr "vite"') do (
        echo Stopping Vite process !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
)

REM Kill Python processes (Flask)
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV ^| findstr "python.exe"') do (
    set pid=%%i
    set pid=!pid:"=!
    for /f "tokens=*" %%j in ('wmic process where "ProcessId=!pid!" get CommandLine /value ^| findstr "simple_api.py"') do (
        echo Stopping Flask process !pid!
        taskkill /PID !pid! /F >nul 2>&1
    )
)

echo.
echo 🎉 CAM Services Stopped Successfully!
echo.
echo 📝 Logs preserved at:
echo   Backend:  logs\backend.log
echo   Frontend: logs\frontend.log
echo.

pause
