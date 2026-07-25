#!/bin/bash
while true; do
    clear
    echo "========================================================="
    echo "       MENU UTAMA BOT WD XLM (VERSI TERMUX)              "
    echo "========================================================="
    echo "1. Install/Update Dependencies (Jalankan ini pertama kali)"
    echo "2. Konek ADB Lokal (Wireless Debugging)"
    echo "3. Jalankan Bot Auto WD XLM"
    echo "0. Keluar"
    echo "========================================================="
    read -p "Pilih menu (0-3): " pilihan

    case $pilihan in
        1)
            echo ""
            bash setup.sh
            echo ""
            read -p "Tekan Enter untuk kembali ke menu..."
            ;;
        2)
            echo ""
            echo "========================================================="
            echo "SYARAT: Nyalakan 'Proses Debug Nirkabel' (Wireless Debugging)"
            echo "di Pengaturan Developer HP Anda sebelum melanjutkan."
            echo "========================================================="
            python termux/konek_adb.py
            echo ""
            read -p "Tekan Enter untuk kembali ke menu..."
            ;;
        3)
            echo ""
            python wd_xlm.py
            echo ""
            read -p "Tekan Enter untuk kembali ke menu..."
            ;;
        0)
            echo "Keluar dari menu..."
            exit 0
            ;;
        *)
            echo "Pilihan tidak valid!"
            sleep 1
            ;;
    esac
done
