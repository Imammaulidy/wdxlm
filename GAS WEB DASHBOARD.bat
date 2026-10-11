@echo off
color 0B
title Web Controller Dashboard (Port 2000) - Bitget Wallet ^& Topnod
cd /d "%~dp0"

echo [*] Mendeteksi IP Otomatis Local LAN...

set LOCAL_IP=
for /f %%i in ('python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]; s.close(); print(ip if ip != '127.0.0.1' and not ip.startswith('0.') else '')" 2^>nul') do set LOCAL_IP=%%i

if "%LOCAL_IP%"=="" (
    for /f "tokens=4" %%a in ('route print 0.0.0.0 ^| findstr /r "0\.0\.0\.0"') do (
        if "%LOCAL_IP%"=="" (
            echo %%a | findstr /r "^192\.168\. ^10\. ^172\." >nul && set LOCAL_IP=%%a
        )
    )
)
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.13

set LOCAL_URL=http://%LOCAL_IP%:2000
set PUBLIC_DOMAIN=https://topnodtools.web.id

:MENU_LOOP
cls
echo ======================================================================
echo    BITGET WALLET AUTO CONTROL DASHBOARD - PORT 2000
echo    DOMAIN PUBLIK: %PUBLIC_DOMAIN%
echo ======================================================================
echo.
echo  [+] IP Otomatis LAN  : %LOCAL_URL%
echo  [+] Domain Cloudflare: %PUBLIC_DOMAIN%
echo ======================================================================
echo.
echo Pilih Mode Operasi Dashboard:
echo.
echo   [1] JALANKAN DENGAN PM2 (Rekomendasi 24 Jam - Aktif Saat Layar Mati)
echo   [2] JALANKAN DI JENDELA INI (Foreground CMD)
echo   [3] LIHAT STATUS ^& MONITOR PM2 (pm2 status)
echo   [4] STOP LAYANAN PM2
echo   [0] KELUAR
echo.

choice /c 12340 /n /m "Pilihan Anda [1-4, atau 0 untuk Keluar]: "
if errorlevel 5 exit /b
if errorlevel 4 goto OP_STOP
if errorlevel 3 goto OP_STATUS
if errorlevel 2 goto OP_FOREGROUND
if errorlevel 1 goto OP_PM2

:OP_PM2
cls
echo ======================================================================
echo    BITGET WALLET AUTO CONTROL DASHBOARD (PORT 2000)
echo    MODE BACKGROUND PM2 (24 JAM NON-STOP SAAT LAYAR LAPTOP MATI)
echo ======================================================================
echo.
echo [*] Mengaktifkan Proteksi Anti-Sleep Windows (Away Mode 24/7)...
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1

echo [*] Memeriksa ketersediaan Port 2000...
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":2000.*LISTENING"') do (
    if "%%a" neq "0" (
        echo  [-] Menghentikan proses lawas di Port 2000 (PID: %%a)...
        taskkill /F /PID %%a /T >nul 2>&1
    )
)

echo [*] Menjalankan Server di Background via PM2...
pm2 delete bitget-server >nul 2>&1
pm2 start core\ecosystem.config.js
pm2 save >nul 2>&1

echo [*] Memasang skrip Auto-Start Windows...
python core\create_autostart.py >nul 2>&1

echo.
echo ======================================================================
echo  [SUKSES] SERVER TELAH BERJALAN DI LATAR BELAKANG DENGAN PM2!
echo ======================================================================
echo  [+] Akses LAN Otomatis : %LOCAL_URL%
echo  [+] Domain Cloudflare  : %PUBLIC_DOMAIN%
echo  [+] Proteksi Screen Off: AKTIF (Aman menutup laptop / layar mati)
echo  [+] Auto-Restart Crash : AKTIF (Dikelola penuh oleh PM2)
echo  [+] Auto-Start Windows : AKTIF (Otomatis jalan saat PC reboot)
echo ======================================================================
echo.
echo [*] Membuka Dashboard di Browser: %LOCAL_URL%
start "" "%LOCAL_URL%"
echo.
echo [INFO] Server berjalan 24 jam non-stop di background.
echo        Jendela ini dapat ditutup kapan saja tanpa mematikan bot/server.
echo.
echo Tekan tombol apa saja untuk kembali ke menu utama...
pause >nul
goto MENU_LOOP

:OP_STATUS
cls
echo ======================================================================
echo    STATUS ^& MONITOR BITGET SERVER DI PM2
echo ======================================================================
echo.
pm2 status bitget-server
echo.
echo ======================================================================
echo    LOG TERAKHIR BITGET SERVER (30 BARIS TERAKHIR)
echo ======================================================================
pm2 logs bitget-server --lines 30 --nostream
echo.
echo Tekan tombol apa saja untuk kembali ke menu utama...
pause >nul
goto MENU_LOOP

:OP_STOP
cls
echo ======================================================================
echo    MENGHENTIKAN BITGET SERVER DI PM2
echo ======================================================================
echo.
pm2 stop bitget-server
pm2 delete bitget-server
pm2 save >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr ":2000.*LISTENING"') do (
    if "%%a" neq "0" (
        taskkill /F /PID %%a /T >nul 2>&1
    )
)
echo.
echo [+] Layanan bitget-server berhasil dihentikan dari PM2.
echo.
echo Tekan tombol apa saja untuk kembali ke menu utama...
pause >nul
goto MENU_LOOP

:OP_FOREGROUND
cls
echo ======================================================================
echo    BITGET WALLET AUTO CONTROL DASHBOARD (PORT 2000)
echo    MODE FOREGROUND CMD
echo ======================================================================
echo.
echo [*] Membuka Browser Otomatis ke: %LOCAL_URL%
start "" "%LOCAL_URL%"

echo [*] Memformat layar HP terkoneksi ke bot screen (1080x2400 @ 352 DPI)...
python -c "import sys; sys.path.insert(0, 'core'); from screen_manager import record_and_apply_bot_screen, get_connected_devices; [record_and_apply_bot_screen(serial=s, silent=True) for s in get_connected_devices()]" >nul 2>&1

echo.
echo [*] Menjalankan Server Controller ^& Cloudflare Tunnel di Port 2000...
echo [*] Tekan Ctrl+C untuk menghentikan server dan kembali ke menu.
echo ======================================================================
python core\server.py
echo.
echo [*] Server Foreground telah berhenti.
echo Tekan tombol apa saja untuk kembali ke menu utama...
pause >nul
goto MENU_LOOP
