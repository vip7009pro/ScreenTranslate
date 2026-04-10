@echo off
REM ScreenTranslate Installer (Batch)
REM This batch file launches the PowerShell installer

setlocal enabledelayedexpansion

echo.
echo ======================================================================
echo ScreenTranslate Setup
echo ======================================================================
echo.

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Check if PowerShell is available
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: PowerShell is not available on this system
    pause
    exit /b 1
)

REM Run the PowerShell installer
echo Launching installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%installer.ps1"

pause
