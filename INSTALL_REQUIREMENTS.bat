@echo off
title UMISKILLS - ENVIRONMENT SETUP (officialum1)
color 0b
echo ==============================================================
echo       UMISKILLS - DEPENDENCY INSTALLER FOR WINDOWS RDP
echo                       by officialum1
echo ==============================================================
echo.
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and check 'Add Python to PATH'.
    pause
    exit /b
)
echo.
echo Installing required packages (requests, beautifulsoup4, dnspython)...
pip install -r requirements.txt
echo.
echo ==============================================================
echo  [SUCCESS] All dependencies installed successfully!
echo  You can now run any of the tools using the .bat launchers.
echo ==============================================================
pause
