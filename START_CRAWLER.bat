@echo off
title UMISKILLS - LEAD MATRIX PRO (by officialum1)
color 0A
cd /d "%~dp0"
cls
echo ==============================================================
echo               UMISKILLS - LEAD MATRIX PRO v2.5
echo            High-Performance Web Crawler & Lead Hunter
echo                       by officialum1
echo ==============================================================
echo.
echo [1/2] Checking Python requirements...
python -m pip install -q requests beautifulsoup4
echo [2/2] Launching UmiSkills Engine...
echo.
python crawler.py
pause
