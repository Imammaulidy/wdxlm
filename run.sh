#!/bin/bash
# ==============================================================================
# BOT AUTO WD XLM, CREATOR & QRIS BITGET — TERMUX ALL-IN-ONE RUNNER
# Mendukung ADB Wireless & Shizuku (rish) Non-Root / Offline Data
# ==============================================================================

# Pindah ke root folder proyek
cd "$(dirname "$0")" || exit 1

# Auto-elevasi root/sudo untuk Linux VPS (non-Termux)
if [ "$(id -u)" -ne 0 ] && [ -z "$PREFIX" ] && command -v sudo >/dev/null 2>&1; then
    echo "[*] Membutuhkan hak akses root/sudo, mengalihkan ke sudo..."
    exec sudo "$0" "$@"
fi

# Setup Environment Shizuku & Library Path
export RISH_APPLICATION_ID="com.termux"
TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
if [ -d "$TERMUX_PREFIX/lib" ]; then
    export LD_LIBRARY_PATH="$TERMUX_PREFIX/lib:$LD_LIBRARY_PATH"
fi

# 1. Setup akses penyimpanan jika belum ada
if [ -d "$HOME" ] && [ ! -d "$HOME/storage" ]; then
    echo "[*] Menyiapkan izin penyimpanan Termux..."
    termux-setup-storage
fi

# 2. Cek & install paket yang diperlukan otomatis
NEED_INSTALL=0
for pkg in python nmap adb curl unzip; do
    if ! command -v "$pkg" &> /dev/null; then
        NEED_INSTALL=1
        break
    fi
done

if [ $NEED_INSTALL -eq 1 ]; then
    echo "[*] Menginstal dependensi Termux (Python, ADB, NMAP, cURL, Unzip)..."
    pkg update -y
    pkg install python nmap android-tools curl unzip -y
    pip install -r Core/requirements.txt
fi

# 3. Siapkan file konfigurasi dari template jika belum ada
if [ ! -f "Core/Json/config.json" ]; then
    if [ -f "Core/Json/config.example.json" ]; then
        cp Core/Json/config.example.json Core/Json/config.json
        echo "[*] Core/Json/config.json berhasil dibuat dari template."
    fi
fi
if [ ! -f "Core/Json/emails.txt" ]; then
    if [ -f "Core/Json/emails.example.txt" ]; then
        cp Core/Json/emails.example.txt Core/Json/emails.txt
        echo "[*] Core/Json/emails.txt berhasil dibuat dari template."
    fi
fi

# Pasang listener pemulihan resolusi layar saat terminal ditutup / exit
restore_screen() {
    python -c "import sys; sys.path.insert(0, 'Core/Python'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" > /dev/null 2>&1
}
trap restore_screen EXIT INT TERM

# Shortcut via Argumen Baris Perintah
if [ "$1" == "--menu" ]; then
    python Core/Python/menu.py
    exit 0
elif [ "$1" == "--wd" ]; then
    python Core/Python/wd_xlm.py
    exit 0
elif [ "$1" == "--wd-old" ]; then
    python Core/Python/wd_xlm.py --old
    exit 0
elif [ "$1" == "--qris" ]; then
    python Core/Python/qris_morph.py
    exit 0
elif [ "$1" == "--server" ]; then
    python Core/Python/server.py
    exit 0
elif [ "$1" == "--connect" ]; then
    python termux/konek_adb.py
    exit 0
fi

# Tampilan Menu Interaktif Termux
while true; do
    clear
    echo "========================================================="
    echo "       BOT AUTO WD XLM BITGET — TERMUX ALL-IN-ONE        "
    echo "========================================================="
    echo " [1] Jalankan Menu Utama All-in-One CLI (menu.py)"
    echo " [2] Jalankan Bot WD XLM — Mode Baru (Import Profil)"
    echo " [3] Jalankan Bot WD XLM — Mode Old (Google Authenticator)"
    echo " [4] Jalankan Bot QRIS Cashback Multi-Chain (qris_morph.py)"
    echo " [5] Jalankan Web Dashboard Controller (Port 2000)"
    echo " [6] Auto-Connect ADB Wireless (termux/konek_adb.py)"
    echo " [7] Setup 1-Klik Shizuku (rish Non-Root / Offline Data)"
    echo " [0] Keluar"
    echo "========================================================="
    read -r -p " Pilih Menu [1-7 / 0]: " pilihan

    case "$pilihan" in
        1)
            echo "[*] Menjalankan Menu Utama..."
            python Core/Python/menu.py
            restore_screen
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        2)
            echo "[*] Menjalankan Bot WD XLM Mode Baru..."
            python Core/Python/wd_xlm.py
            restore_screen
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        3)
            echo "[*] Menjalankan Bot WD XLM Mode Old..."
            python Core/Python/wd_xlm.py --old
            restore_screen
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        4)
            echo "[*] Menjalankan Bot QRIS Cashback..."
            python Core/Python/qris_morph.py
            restore_screen
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        5)
            echo "[*] Menjalankan Web Dashboard Server di Port 2000..."
            echo "[*] Tekan Ctrl+C untuk berhenti dan kembali ke menu."
            python Core/Python/server.py
            restore_screen
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        6)
            echo "[*] Memeriksa & Mengkoneksikan ADB Wireless..."
            python termux/konek_adb.py
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        7)
            echo "[*] Menjalankan Setup Shizuku (rish)..."
            bash termux/setup_shizuku.sh
            read -r -p "Tekan Enter untuk kembali ke menu..." dummy
            ;;
        0)
            echo "[*] Keluar dari runner."
            restore_screen
            exit 0
            ;;
        *)
            echo "[!] Pilihan tidak valid!"
            sleep 1
            ;;
    esac
done
