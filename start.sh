#!/usr/bin/env bash

# Rubika Self-Bot Launcher for Linux / Termux
cd "$(dirname "$0")"

echo "=================================================="
echo "             RUBIKA SELF-BOT LAUNCHER             "
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[-] Python 3 could not be found! Please install python3."
    exit 1
fi

# Create virtualenv if not exists
if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate virtualenv
source venv/bin/activate

# Install requirements
if ! python3 -c "import rubpy" &> /dev/null; then
    echo "[*] Installing required libraries..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Run the Self-Bot
echo "[*] Launching Self-Bot..."
python3 selfbot.py
