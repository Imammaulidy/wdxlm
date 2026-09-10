#!/bin/bash

# Pindah ke root folder proyek
cd "$(dirname "$0")" || exit 1

echo "========================================================="
echo "       BOT AUTO WD XLM BITGET — TERMUX ALL-IN-ONE        "
echo "========================================================="

# 1. Setup akses penyimpanan jika belum ada
if [ ! -d "$HOME/storage" ]; then
    echo "[*] Menyiapkan izin penyimpanan Termux..."
    termux-setup-storage
fi

# 2. Cek & install paket yang diperlukan otomatis
NEED_INSTALL=0
if ! command -v python &> /dev/null; then
    NEED_INSTALL=1
fi
if ! command -v adb &> /dev/null; then
    NEED_INSTALL=1
fi
if ! command -v nmap &> /dev/null; then
    NEED_INSTALL=1
fi

if [ $NEED_INSTALL -eq 1 ]; then
    echo "[*] Menginstal dependensi (Python, ADB, NMAP)..."
    pkg update -y
    pkg install python nmap android-tools -y
fi

# 3. Siapkan file konfigurasi dari template jika belum ada
if [ ! -f "core/config.json" ]; then
    if [ -f "core/config.example.json" ]; then
        cp core/config.example.json core/config.json
        echo "[*] core/config.json berhasil dibuat dari template."
    fi
fi

# 4. Jalankan Menu Utama Bot
python core/menu.py
