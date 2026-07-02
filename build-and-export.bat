@echo off
REM ============================================================
REM Infinite-Canvas Docker 镜像打包导出脚本（Windows 一键启动）
REM ============================================================
REM 功能：调用 build-and-export.ps1 完成镜像打包导出
REM ============================================================

echo 正在启动 Docker 镜像打包导出脚本...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0build-and-export.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
pause
