@echo off
title UMISKILLS - MULTI-NICHE & AUTOMOTIVE LEAD EXTRACTOR (by officialum1)
color 0A
cd /d "%~dp0"
cls
echo ==============================================================
echo       UMISKILLS - MULTI-NICHE & AUTOMOTIVE LEAD EXTRACTOR
echo                       by officialum1
echo ==============================================================
echo.
echo [1/2] Checking Python requirements...
python -m pip install -q requests beautifulsoup4
echo [2/2] Launching Craigslist Email & Lead Extractor...
echo.
python craigslist_email_extractor.py
pause
