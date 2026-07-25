#!/bin/bash

echo "========================================================="
echo "       INSTALLER BOT AUTO WD XLM UNTUK TERMUX            "
echo "========================================================="
echo ""

# Meminta izin akses penyimpanan (agar bisa mengakses file dari memori internal jika diperlukan)
termux-setup-storage

echo "[1/4] Melakukan Update & Upgrade repository Termux..."
pkg update -y && pkg upgrade -y

echo ""
echo "[2/4] Menginstal Python, NMAP, dan ADB (Android Tools)..."
pkg install python nmap android-tools -y

echo "[3/4] Menyiapkan File Konfigurasi Dasar..."
if [ ! -f "config.json" ]; then
    cp config.example.json config.json
    echo "  -> config.json berhasil dibuat dari config.example.json"
else
    echo "  -> config.json sudah ada, melewatinya."
fi

echo ""
echo "[4/4] Setup Selesai!"
echo "========================================================="
echo "Ketik perintah berikut untuk menjalankan menu utama:"
echo "   bash termux.sh"
echo "========================================================="
