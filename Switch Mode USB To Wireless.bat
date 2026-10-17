@echo off
:: ======================================================================
:: SWITCH MODE SCRCPY - USB <-> WIRELESS 120 FPS (ALL-IN-ONE)
:: Auto-Elevasi Administrator UAC (Rule #7) & Anti-Mental
:: ======================================================================

if "%1"==":direct" goto :run_main

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/k %~s0 :direct' -Verb RunAs"
    exit /b
)

:run_main
cd /d "%~dp0"
title SWITCH MODE SCRCPY - USB / WIRELESS (120 FPS)
color 0b

:: ----------------------------------------------------------------------
:: 1. Inisialisasi Path Binary Resmi
:: ----------------------------------------------------------------------
if exist "%~dp0Core\scrcpy-win64-v3.3.4\adb.exe" (
    set "ADB_BIN=%~dp0Core\scrcpy-win64-v3.3.4\adb.exe"
    set "SCRCPY_DIR=%~dp0Core\scrcpy-win64-v3.3.4"
    set "SCRCPY_BIN=%~dp0Core\scrcpy-win64-v3.3.4\scrcpy.exe"
    set "NOCONSOLE_VBS=%~dp0Core\scrcpy-win64-v3.3.4\scrcpy-noconsole.vbs"
) else if exist "%~dp0core\scrcpy-win64-v3.3.4\adb.exe" (
    set "ADB_BIN=%~dp0core\scrcpy-win64-v3.3.4\adb.exe"
    set "SCRCPY_DIR=%~dp0core\scrcpy-win64-v3.3.4"
    set "SCRCPY_BIN=%~dp0core\scrcpy-win64-v3.3.4\scrcpy.exe"
    set "NOCONSOLE_VBS=%~dp0core\scrcpy-win64-v3.3.4\scrcpy-noconsole.vbs"
) else (
    set "ADB_BIN=adb"
    set "SCRCPY_DIR=%~dp0"
    set "SCRCPY_BIN=scrcpy"
    set "NOCONSOLE_VBS="
)

"%ADB_BIN%" start-server >nul 2>&1

:MENU
cd /d "%~dp0"
cls
echo ======================================================================
echo       SWITCH MODE SCRCPY MIRRORING - USB ^<--^> WIRELESS (120 FPS)
echo ======================================================================
echo.

:: Deteksi Perangkat USB dan Wireless
set "USB_DEV="
set "WIFI_DEV="
set "WIFI_IP="

for /f "tokens=1,2" %%a in ('"%ADB_BIN%" devices') do (
    if "%%b"=="device" (
        echo %%a | findstr ":" >nul
        if errorlevel 1 (
            set "USB_DEV=%%a"
        ) else (
            set "WIFI_DEV=%%a"
        )
    )
)

if defined USB_DEV (
    echo  [+] Perangkat USB Kabel  : TERHUBUNG [%USB_DEV%]
) else (
    echo  [-] Perangkat USB Kabel  : Tidak Terhubung
)

if defined WIFI_DEV (
    echo  [+] Perangkat Wireless   : TERHUBUNG [%WIFI_DEV%]
) else (
    echo  [-] Perangkat Wireless   : Tidak Terhubung
)
echo ======================================================================
echo.
echo Pilih Aksi:
echo.
echo   [1] JALANKAN MODE USB MURNI (120 FPS - Zero Latency)
echo       * Memprioritaskan kabel USB murni tanpa Wi-Fi.
echo       * Layar HP fisik mati (-S), terminal otomatis tertutup.
echo.
echo   [2] SWITCH KE WIRELESS ^& JALANKAN (120 FPS - Bebas Kabel)
echo       * Mengaktifkan TCP/IP 5555 ^& mendeteksi IP Wi-Fi otomatis.
echo       * Kabel USB bisa langsung dicabut setelah layar tampil.
echo       * Terminal otomatis tertutup setelah layar muncul.
echo.
echo   [3] HANYA SWITCH KE WIRELESS (Aktifkan port 5555 tanpa buka layar)
echo       * Siapkan ADB Wireless agar HP bisa dicabut dan dipakai Bot.
echo.
echo   [4] PUTUSKAN KONEKSI WIRELESS (Kembalikan murni ke USB)
echo       * Memutuskan semua koneksi TCP/IP (adb disconnect).
echo.
echo   [5] CEK DETAIL INFORMASI PERANGKAT (IP, Baterai, Model)
echo.
echo   [0] KELUAR
echo.
echo ======================================================================

choice /c 123450 /n /m "Pilihan Anda (1-5 / 0): "
if errorlevel 6 exit
if errorlevel 5 goto CHECK_INFO
if errorlevel 4 goto DISCONNECT_WIRELESS
if errorlevel 3 goto ONLY_SWITCH_WIRELESS
if errorlevel 2 goto SWITCH_AND_RUN_WIRELESS
if errorlevel 1 goto RUN_USB_PURE
goto MENU

:: ======================================================================
:: 1. RUN USB MURNI (120 FPS)
:: ======================================================================
:RUN_USB_PURE
cls
echo ======================================================================
echo       MENJALANKAN SCRCPY MODE USB MURNI (120 FPS - ZERO LATENCY)
echo ======================================================================
echo.

if not defined USB_DEV (
    color 0c
    echo [ERROR] Kabel USB belum terhubung atau USB Debugging belum aktif!
    echo.
    echo 1. Hubungkan kabel USB dari HP ke PC.
    echo 2. Pastikan Opsi Pengembang -^> Debugging USB aktif di HP.
    echo 3. Jika muncul popup di HP, centang 'Selalu izinkan'.
    echo.
    echo Tekan sembarang tombol untuk kembali ke menu...
    pause >nul
    color 0b
    goto MENU
)

echo [*] Perangkat USB : %USB_DEV%
echo [*] Konfigurasi   : 120 FPS, Layar Fisik Dimatikan (-S), Wake Device (-w)
echo [*] Membuka SCRCPY via USB murni...
echo.
echo [+] SCRCPY sedang diluncurkan!
echo [*] Jendela terminal ini akan otomatis ditutup dalam 2 detik...

cd /d "%SCRCPY_DIR%"
if exist "%NOCONSOLE_VBS%" (
    start "" wscript.exe "%NOCONSOLE_VBS%" -s %USB_DEV% -S -w --max-fps=120
) else (
    powershell -NoProfile -Command "Start-Process -FilePath '%SCRCPY_BIN%' -ArgumentList '-s %USB_DEV% -S -w --max-fps=120' -WindowStyle Hidden"
)

timeout /t 2 /nobreak >nul
exit

:: ======================================================================
:: 2. SWITCH KE WIRELESS & JALANKAN SCRCPY (120 FPS)
:: ======================================================================
:SWITCH_AND_RUN_WIRELESS
cls
echo ======================================================================
echo     SWITCH KE WIRELESS ^& MENJALANKAN SCRCPY (120 FPS - BEBAS KABEL)
echo ======================================================================
echo.

:: Jika belum ada wireless device yang terkoneksi, setup via USB
if not defined WIFI_DEV (
    if not defined USB_DEV (
        color 0c
        echo [ERROR] Tidak ada perangkat USB yang terhubung untuk inisialisasi awal!
        echo.
        echo Untuk berpindah ke mode Wireless pertama kali:
        echo 1. Colokkan kabel USB ke HP sebentar saja.
        echo 2. Pastikan HP dan PC terhubung ke jaringan Wi-Fi yang sama.
        echo 3. Jalankan menu ini kembali.
        echo.
        echo Tekan sembarang tombol untuk kembali ke menu...
        pause >nul
        color 0b
        goto MENU
    )

    echo [*] Mengaktifkan mode TCP/IP pada port 5555 di perangkat USB...
    "%ADB_BIN%" -s %USB_DEV% tcpip 5555
    timeout /t 2 /nobreak >nul

    echo [*] Mendeteksi alamat IP Wi-Fi perangkat Android...
    for /f "tokens=2 delims= " %%i in ('"%ADB_BIN%" -s %USB_DEV% shell ip -f inet addr show wlan0 ^| findstr /r "inet.*brd"') do (
        for /f "tokens=1 delims=/" %%a in ("%%i") do set "WIFI_IP=%%a"
    )

    if not defined WIFI_IP (
        for /f "tokens=2 delims= " %%i in ('"%ADB_BIN%" -s %USB_DEV% shell ip -f inet addr show wlan1 ^| findstr /r "inet.*brd"') do (
            for /f "tokens=1 delims=/" %%a in ("%%i") do set "WIFI_IP=%%a"
        )
    )

    if not defined WIFI_IP (
        color 0c
        echo [ERROR] Gagal mendeteksi alamat IP Wi-Fi pada perangkat!
        echo Pastikan Wi-Fi pada HP sudah aktif dan terhubung ke router.
        echo.
        echo Tekan sembarang tombol untuk kembali ke menu...
        pause >nul
        color 0b
        goto MENU
    )

    echo [+] IP Wi-Fi Terdeteksi: %WIFI_IP%
    echo [*] Menghubungkan ADB ke %WIFI_IP%:5555...
    "%ADB_BIN%" connect %WIFI_IP%:5555
    set "TARGET_DEV=%WIFI_IP%:5555"
) else (
    set "TARGET_DEV=%WIFI_DEV%"
    echo [+] Menggunakan perangkat wireless yang sudah aktif: %TARGET_DEV%
)

echo.
echo ======================================================================
echo [SUKSES BESAR] Mode Wireless Aktif di: %TARGET_DEV%
echo [INFO PENTING] ANDA SEKARANG SUDAH AMAN UNTUK MENCABUT KABEL USB!
echo ======================================================================
echo.
echo [*] Membuka SCRCPY Wireless (120 FPS, Layar Fisik Dimatikan)...
echo [*] Jendela terminal ini akan otomatis ditutup dalam 3 detik...

cd /d "%SCRCPY_DIR%"
if exist "%NOCONSOLE_VBS%" (
    start "" wscript.exe "%NOCONSOLE_VBS%" -s %TARGET_DEV% -S -w --max-fps=120
) else (
    powershell -NoProfile -Command "Start-Process -FilePath '%SCRCPY_BIN%' -ArgumentList '-s %TARGET_DEV% -S -w --max-fps=120' -WindowStyle Hidden"
)

timeout /t 3 /nobreak >nul
exit

:: ======================================================================
:: 3. HANYA AKTIFKAN WIRELESS TANPA BUKA LAYAR
:: ======================================================================
:ONLY_SWITCH_WIRELESS
cls
echo ======================================================================
echo          AKTIFKAN MODE ADB WIRELESS (UNTUK PENGGUNAAN BOT)
echo ======================================================================
echo.

if not defined USB_DEV (
    if defined WIFI_DEV (
        echo [INFO] ADB Wireless sudah aktif di %WIFI_DEV%.
        pause
        goto MENU
    )
    color 0c
    echo [ERROR] Colokkan kabel USB terlebih dahulu untuk mengaktifkan port wireless!
    pause >nul
    color 0b
    goto MENU
)

echo [*] Mengaktifkan TCP/IP port 5555...
"%ADB_BIN%" -s %USB_DEV% tcpip 5555
timeout /t 2 /nobreak >nul

for /f "tokens=2 delims= " %%i in ('"%ADB_BIN%" -s %USB_DEV% shell ip -f inet addr show wlan0 ^| findstr /r "inet.*brd"') do (
    for /f "tokens=1 delims=/" %%a in ("%%i") do set "WIFI_IP=%%a"
)

if not defined WIFI_IP (
    color 0c
    echo [ERROR] Gagal mendeteksi IP Wi-Fi! Periksa koneksi Wi-Fi HP.
    pause >nul
    color 0b
    goto MENU
)

echo [*] Menyambungkan ADB ke %WIFI_IP%:5555...
"%ADB_BIN%" connect %WIFI_IP%:5555
echo.
echo [SUKSES] ADB Wireless AKTIF di %WIFI_IP%:5555!
echo Kabel USB sekarang boleh dicabut. Bot dapat berjalan tanpa kabel.
echo.
pause
goto MENU

:: ======================================================================
:: 4. PUTUSKAN WIRELESS & KEMBALIKAN KE USB
:: ======================================================================
:DISCONNECT_WIRELESS
cls
echo ======================================================================
echo                 MEMUTUSKAN KONEKSI ADB WIRELESS
echo ======================================================================
echo.
echo [*] Memutuskan semua sambungan TCP/IP...
"%ADB_BIN%" disconnect
echo.
echo [OK] Semua koneksi Wireless berhasil diputus.
echo Sistem kini murni memprioritaskan kabel USB fisik.
echo.
pause
goto MENU

:: ======================================================================
:: 5. CEK DETAIL INFORMASI PERANGKAT
:: ======================================================================
:CHECK_INFO
cls
echo ======================================================================
echo                       INFORMASI PERANGKAT ADB
echo ======================================================================
echo.
"%ADB_BIN%" devices -l
echo.
echo ----------------------------------------------------------------------
if defined USB_DEV (
    echo [Perangkat USB: %USB_DEV%]
    for /f "tokens=*" %%m in ('"%ADB_BIN%" -s %USB_DEV% shell getprop ro.product.model 2^>nul') do echo  - Model HP     : %%m
    for /f "tokens=*" %%b in ('"%ADB_BIN%" -s %USB_DEV% shell dumpsys battery ^| findstr "level" 2^>nul') do echo  - Baterai      : %%b%%
    for /f "tokens=2 delims= " %%i in ('"%ADB_BIN%" -s %USB_DEV% shell ip -f inet addr show wlan0 2^>nul ^| findstr /r "inet.*brd"') do (
        for /f "tokens=1 delims=/" %%a in ("%%i") do echo  - IP Wi-Fi     : %%a
    )
)
if defined WIFI_DEV (
    echo.
    echo [Perangkat Wireless: %WIFI_DEV%]
    for /f "tokens=*" %%m in ('"%ADB_BIN%" -s %WIFI_DEV% shell getprop ro.product.model 2^>nul') do echo  - Model HP     : %%m
    for /f "tokens=*" %%b in ('"%ADB_BIN%" -s %WIFI_DEV% shell dumpsys battery ^| findstr "level" 2^>nul') do echo  - Baterai      : %%b%%
)
echo ----------------------------------------------------------------------
echo.
pause
goto MENU
