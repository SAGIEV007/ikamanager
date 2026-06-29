@echo off
REM IkaManager - Quick Start Script for Windows
REM Double-click this file to start the application

echo ======================================
echo   IkaManager - Starting...
echo ======================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running!
    echo.
    echo Please install and start Docker Desktop:
    echo   https://docs.docker.com/desktop/install/windows-install/
    echo.
    pause
    exit /b 1
)

echo Building and starting services...
echo.

docker compose up --build -d

echo.
echo ======================================
echo   IkaManager is running!
echo.
echo   Open in your browser:
echo   http://localhost:3000
echo.
echo   To stop: docker compose down
echo ======================================
echo.
pause
