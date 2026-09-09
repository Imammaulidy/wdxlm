#!/bin/bash
if ! command -v python &> /dev/null
then
    echo "Python belum terinstall! Menjalankan setup.sh terlebih dahulu..."
    bash termux/setup.sh
fi

python core/menu.py
