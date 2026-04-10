@echo off
REM ScreenTranslate Application Launcher

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Set up environment variables
set PYTHONPATH=%SCRIPT_DIR%
set TESSDATA_PREFIX=%SCRIPT_DIR%tessdata

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo.
    echo Error: Virtual environment not found
    echo.
    echo Please run setup.bat first to install dependencies
    echo.
    pause
    exit /b 1
)

REM Set up the virtual environment
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"

REM Check for Tesseract
echo Checking for Tesseract-OCR...

set TESSERACT_FOUND=0

if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    set SCREEN_TRANSLATE_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
    set TESSERACT_FOUND=1
)

if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
    set SCREEN_TRANSLATE_TESSERACT_CMD=C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
    set TESSERACT_FOUND=1
)

if !TESSERACT_FOUND! equ 0 (
    echo.
    echo Warning: Tesseract-OCR not found in standard locations
    echo.
    echo Please install Tesseract-OCR from:
    echo https://github.com/UB-Mannheim/tesseract/releases
    echo.
    echo Or set SCREEN_TRANSLATE_TESSERACT_CMD environment variable
    echo.
    echo Attempting to continue anyway...
)

REM Run the application
echo.
echo ======================================================================
echo Starting ScreenTranslate...
echo ======================================================================
echo.
echo Press Ctrl+Shift+E to activate the screen translation
echo.
echo ======================================================================
echo.

"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%screen_overlay_translator.py"

REM If the Python script exited, pause to see any error messages
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code: %errorlevel%
    echo.
    pause
)
