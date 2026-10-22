@echo off
title UMISKILLS - STOP SYSTEM
color 0c
cls
echo ==============================================================
echo       UMISKILLS - STOPPING ALL BACKGROUND WORKERS
echo                       by officialum1
echo ==============================================================
echo.
echo Terminating background harvester and dashboard server...
taskkill /F /IM python.exe >nul 2>&1
echo.
echo [SUCCESS] All background processes stopped cleanly.
echo.
pause
