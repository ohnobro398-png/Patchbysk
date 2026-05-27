#!/bin/bash
# ============================================================
# APK-X ENTERPRISE SUITE v11.0 - Auto Setup Script
# Architect: Jim (30yr EXP) | Developer: Bob
# ============================================================

set -e

echo "========================================"
echo " APK-X ENTERPRISE SUITE v11.0 SETUP"
echo "========================================"

# Detect OS
if [ -d "/data/data/com.termux" ]; then
    OS="termux"
    echo "[*] Termux detected"
else
    OS="linux"
    echo "[*] Linux detected"
fi

# Install system dependencies
if [ "$OS" = "termux" ]; then
    echo "[1/4] Installing Termux packages..."
    pkg update -y && pkg upgrade -y
    pkg install python openjdk-17 aapt apksigner apktool git wget curl -y
else
    echo "[1/4] Installing system packages..."
    sudo apt update -y
    sudo apt install python3 python3-pip openjdk-17-jdk aapt apksigner apktool git wget curl -y
fi

# Install Python packages
echo "[2/4] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
echo "[3/4] Creating directories..."
mkdir -p /sdcard/APKX_Enterprise/{Output,Backups,Logs,Database,Plugins,Temp,Reports}
mkdir -p ~/APKX_Enterprise/plugins
mkdir -p ~/APKX_Enterprise/docs

# Make script executable
echo "[4/4] Setting permissions..."
chmod +x main.py
chmod +x setup.sh

echo ""
echo "========================================"
echo " ✅ SETUP COMPLETE!"
echo "========================================"
echo ""
echo "Usage:"
echo "  python main.py dashboard"
echo "  python main.py patch /sdcard/app.apk"
echo "  python main.py stats"
echo ""