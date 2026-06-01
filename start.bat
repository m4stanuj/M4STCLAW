@echo off
title M4STCLAW Core Server Launcher
echo ===================================================================
echo             M4STCLAW v3.3.0 — Autonomous Mesh Network
echo ===================================================================
echo.
echo Launching local python server environment...
python start.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python failed to start start.py. Please verify python is installed and on PATH.
    pause
)
