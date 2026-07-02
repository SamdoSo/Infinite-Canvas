@echo off
REM ============================================================
REM Infinite-Canvas Docker Image Build & Export Script (Windows)
REM ============================================================
REM Usage: Calls build-and-export.ps1 to build and export image
REM ============================================================

echo Starting Docker image build and export...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0build-and-export.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Build failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
pause
