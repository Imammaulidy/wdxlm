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

echo ""
echo "[3/4] Setup Selesai!"
echo "========================================================="
echo "Cara menggunakan Bot secara Nirkabel (Wireless) di Termux:"
echo "1. Aktifkan 'Proses Debug Nirkabel' (Wireless Debugging) di Pengaturan Developer HP Anda."
echo "2. Buka kembali Termux dan ketik perintah ini untuk mencari port otomatis:"
echo "   python termux/konek_adb.py"
echo "3. Jika sudah tertulis SUKSES terkoneksi, jalankan bot dengan:"
echo "   python wd_xlm.py"
echo "========================================================="
