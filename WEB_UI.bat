@echo off
color 0B
title Web UI Dashboard - Bot Auto WD XLM Bitget
echo =========================================================
echo    MEMULAI WEB DASHBOARD BOT AUTO WD XLM BITGET
echo =========================================================
echo  [+] Web UI siap diakses melalui browser:
echo      http://127.0.0.1:5000
echo      http://localhost:5000
echo  [+] Layar HP asli otomatis terekam ^& diproteksi auto-restore.
echo =========================================================
echo.
start "" "http://127.0.0.1:5000"
python core\server.py
python -c "import sys; sys.path.insert(0, 'core'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" >nul 2>&1
pause
