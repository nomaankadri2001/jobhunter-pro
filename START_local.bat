@echo off
title JobHunter Pro
cd /d "%~dp0"
echo.
echo  ======================================
echo   JobHunter Pro  -  Starting...
echo  ======================================
echo.
echo  Keep this window open while using app.
echo  Press Ctrl+C to stop.
echo.
python server.py
pause
