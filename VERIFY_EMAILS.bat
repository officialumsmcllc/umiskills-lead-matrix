@echo off
title UMISKILLS - EMAIL VERIFIER & BOUNCE SHIELD (by officialum1)
color 0A
cd /d "%~dp0"
cls
echo ==============================================================
echo       UMISKILLS - EMAIL VERIFIER & BOUNCE SHIELD v2.5
echo                       by officialum1
echo ==============================================================
echo.
echo [1/2] Checking verification requirements...
python -m pip install -q dnspython
echo [2/2] Running Multi-Threaded MX & SMTP Deliverability Check...
echo.
python email_verifier.py
pause
