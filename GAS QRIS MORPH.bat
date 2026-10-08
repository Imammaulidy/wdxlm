@echo off
color 0B
title Bot ADB Bitget Wallet QRIS Morph L2
python core\qris_morph.py
python -c "import sys; sys.path.insert(0, 'core'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" >nul 2>&1
pause
