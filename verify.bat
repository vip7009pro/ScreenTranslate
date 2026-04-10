@echo off
REM ScreenTranslate Package Verification Script
REM This script checks if all files are present for distribution

setlocal enabledelayedexpansion

echo.
echo ======================================================================
echo ScreenTranslate Package Verification
echo ======================================================================
echo.

set SCRIPT_DIR=%~dp0
set ERRORS=0

REM Check main files
echo Checking required files...
echo.

set /A FOUND=0
if exist "%SCRIPT_DIR%screen_overlay_translator.py" (
    echo [OK] screen_overlay_translator.py
    set /A FOUND+=1
) else (
    echo [MISSING] screen_overlay_translator.py
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%requirements.txt" (
    echo [OK] requirements.txt
    set /A FOUND+=1
) else (
    echo [MISSING] requirements.txt
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%setup.bat" (
    echo [OK] setup.bat
    set /A FOUND+=1
) else (
    echo [MISSING] setup.bat
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%run.bat" (
    echo [OK] run.bat
    set /A FOUND+=1
) else (
    echo [MISSING] run.bat
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%installer.ps1" (
    echo [OK] installer.ps1
    set /A FOUND+=1
) else (
    echo [MISSING] installer.ps1
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%build.py" (
    echo [OK] build.py
    set /A FOUND+=1
) else (
    echo [MISSING] build.py
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%README.md" (
    echo [OK] README.md
    set /A FOUND+=1
) else (
    echo [MISSING] README.md
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%README.vi.md" (
    echo [OK] README.vi.md
    set /A FOUND+=1
) else (
    echo [MISSING] README.vi.md
    set /A ERRORS+=1
)

if exist "%SCRIPT_DIR%PACKAGING.md" (
    echo [OK] PACKAGING.md
    set /A FOUND+=1
) else (
    echo [MISSING] PACKAGING.md
    set /A ERRORS+=1
)

REM Check tessdata
echo.
echo Checking OCR language data...
echo.

set /A LANGS=0
for %%F in ("%SCRIPT_DIR%tessdata\*.traineddata") do (
    echo [OK] %%~nF
    set /A LANGS+=1
)

if !LANGS! equ 0 (
    echo [WARNING] No tessdata files found
    set /A ERRORS+=1
)

REM Summary
echo.
echo ======================================================================
echo Verification Summary
echo ======================================================================
echo.
echo Files found: !FOUND!/9
echo OCR languages: !LANGS!/5
echo Errors: !ERRORS!
echo.

if !ERRORS! equ 0 (
    echo Status: ✓ All files present. Ready to package and distribute.
    echo.
    echo Next steps:
    echo   1. To create a simple ZIP: 
    echo      powershell -Command "Compress-Archive -Path . -DestinationPath ScreenTranslate.zip -Force"
    echo.
    echo   2. To create a standalone EXE:
    echo      python build.py
    echo.
    echo   3. See PACKAGING.md for detailed distribution instructions.
) else (
    echo Status: ✗ Some files are missing. Please check your installation.
)

echo.
pause
