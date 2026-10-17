@echo off
:: ======================================================================
:: SWITCH MODE SCRCPY - USB <-> WIRELESS 120 FPS (ALL-IN-ONE)
:: Auto-Elevasi Administrator UAC (Rule #7) & Anti-Mental
:: ======================================================================

if "%1"==":direct" goto :run_main

net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c %~s0 :direct' -Verb RunAs"
    exit /b
)

:run_main
cd /d "%~dp0"
title SWITCH MODE SCRCPY - USB / WIRELESS (120 FPS)
color 0b

:: ----------------------------------------------------------------------
:: Deteksi Python Interpreter
:: ----------------------------------------------------------------------
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

:MENU
cd /d "%~dp0"
cls
echo ======================================================================
echo       SWITCH MODE SCRCPY MIRRORING - USB ^<--^> WIRELESS (120 FPS)
echo ======================================================================
echo.
"%PY_BIN%" Core\Python\scrcpy_launcher.py --info
echo.
echo Pilih Aksi:
echo.
echo   [1] JALANKAN MODE USB MURNI (120 FPS - Zero Latency)
echo       * Mengunci koneksi lewat kabel USB murni tanpa Wi-Fi.
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
echo   [5] REFRESH / CEK STATUS ULANG
echo.
echo   [0] KELUAR
echo.
echo ======================================================================

choice /c 123450 /n /m "Pilihan Anda (1-5 / 0): "
if errorlevel 6 exit /b 0
if errorlevel 5 goto MENU
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
"%PY_BIN%" Core\Python\scrcpy_launcher.py --usb
if errorlevel 1 (
    echo.
    echo Tekan sembarang tombol untuk kembali ke menu...
    pause >nul
    goto MENU
)
echo [*] Menutup jendela terminal otomatis dalam 2 detik...
timeout /t 2 /nobreak >nul
exit /b 0

:: ======================================================================
:: 2. SWITCH KE WIRELESS & JALANKAN SCRCPY (120 FPS)
:: ======================================================================
:SWITCH_AND_RUN_WIRELESS
cls
"%PY_BIN%" Core\Python\scrcpy_launcher.py --switch-wireless
if errorlevel 1 (
    echo.
    echo Tekan sembarang tombol untuk kembali ke menu...
    pause >nul
    goto MENU
)
echo [*] Menutup jendela terminal otomatis dalam 2 detik...
timeout /t 2 /nobreak >nul
exit /b 0

:: ======================================================================
:: 3. HANYA AKTIFKAN WIRELESS TANPA BUKA LAYAR
:: ======================================================================
:ONLY_SWITCH_WIRELESS
cls
"%PY_BIN%" Core\Python\scrcpy_launcher.py --setup-wireless-only
echo.
pause
goto MENU

:: ======================================================================
:: 4. PUTUSKAN WIRELESS & KEMBALIKAN KE USB
:: ======================================================================
:DISCONNECT_WIRELESS
cls
"%PY_BIN%" Core\Python\scrcpy_launcher.py --disconnect
echo.
pause
goto MENU
