#!/bin/bash
if ! command -v python &> /dev/null
then
    echo "Python belum terinstall! Menjalankan setup.sh terlebih dahulu..."
    bash setup.sh
fi

python menu.py
