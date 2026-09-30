@echo off
title Rubika Self-Bot Launcher
chcp 65001 > nul 2>&1
cd /d "%~dp0"

echo ==================================================
echo             RUBIKA SELF-BOT LAUNCHER              
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [-] Python is not installed or not in PATH!
    echo [!] Please install Python from https://www.python.org/downloads/
    echo [!] Make sure to check Add Python to PATH during installation.
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv\Scripts\activate.bat" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check and install requirements
python -c "import rubpy" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required libraries...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

REM Run the Self-Bot
echo [*] Launching Self-Bot...
python selfbot.py

echo.
echo [*] Self-Bot session ended.
pause
