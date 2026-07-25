@echo off
echo ========================================================
echo       MEMBUNUH SEMUA PROSES ADB YANG NYANGKUT
echo ========================================================
echo.
echo [*] Menghentikan adb.exe...
taskkill /F /IM adb.exe /T >nul 2>&1
echo [*] Menghentikan QtScrcpy.exe (jika ada)...
taskkill /F /IM QtScrcpy.exe /T >nul 2>&1
echo [*] Menghentikan scrcpy.exe (jika ada)...
taskkill /F /IM scrcpy.exe /T >nul 2>&1
echo.
echo [!] Semua proses latar belakang berhasil dibersihkan!
echo.
pause
