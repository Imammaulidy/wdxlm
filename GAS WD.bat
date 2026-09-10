@echo off
color 0A
title Menu Utama Bot Auto WD XLM Bitget
python core\menu.py
python -c "import sys; sys.path.insert(0, 'core'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" >nul 2>&1
pause

