#!/bin/bash

# Pindah ke root folder proyek jika script dijalankan langsung dari dalam folder termux/
cd "$(dirname "$0")/.." || exit 1

echo "========================================================="
echo "       INSTALLER BOT AUTO WD XLM UNTUK TERMUX            "
echo "========================================================="
echo ""

# Meminta izin akses penyimpanan
termux-setup-storage

echo "[1/4] Melakukan Update & Upgrade repository Termux..."
pkg update -y && pkg upgrade -y

echo ""
echo "[2/4] Menginstal Python, NMAP, dan ADB (Android Tools)..."
pkg install python nmap android-tools -y

echo "[3/4] Menyiapkan File Konfigurasi Dasar..."
if [ ! -f "core/config.json" ]; then
    if [ -f "core/config.example.json" ]; then
        cp core/config.example.json core/config.json
        echo "  -> core/config.json berhasil dibuat dari template"
    fi
else
    echo "  -> core/config.json sudah ada, melewatinya."
fi

echo ""
echo "[4/4] Setup Selesai!"
echo "========================================================="
echo "Ketik perintah berikut untuk menjalankan menu utama:"
echo "   bash termux.sh"
echo "========================================================="
