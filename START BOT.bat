@echo off
:: ======================================================================
:: BITGET WALLET TOOLS - ALL IN ONE CONTROLLER (TRIO MERAK)
:: Auto-Elevasi UAC Administrator (Rule #7) & Smart Auto-Dependency
:: ======================================================================

:: 1. Verifikasi dan Auto-Elevasi UAC Administrator (Anti-Mental)
if "%1"==":direct" goto :run_main
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/k %~s0 :direct' -Verb RunAs"
    exit /b
)

:run_main
cd /d "%~dp0"
title BITGET WALLET TOOLS - ALL IN ONE CONTROLLER
color 0a

:: ======================================================================
:: 2. Smart Virtual Environment (.venv) & Fast Dependency Checker
:: ======================================================================
if exist ".venv\Scripts\python.exe" goto :CHECK_DEPENDENCIES

echo ======================================================================
echo   [INFO] Virtual Environment [.venv] belum ditemukan.
echo   Membuat .venv baru dan menginstall seluruh dependensi otomatis...
echo ======================================================================
where python >nul 2>&1
if errorlevel 1 (
    color 0c
    echo [ERROR] Python belum terinstall di komputer ini atau belum masuk ke PATH!
    echo Silakan unduh dan install Python 3.10+ dari https://www.python.org/
    echo Pastikan centang Add Python to PATH saat menginstall.
    pause
    exit /b 1
)

python -m venv .venv
if errorlevel 1 (
    color 0c
    echo [ERROR] Gagal membuat virtual environment .venv!
    pause
    exit /b 1
)

echo [*] Mengupgrade pip dan wheel...
call .venv\Scripts\python.exe -m pip install --upgrade pip wheel >nul 2>&1
echo [*] Menginstall pustaka dari Core\requirements.txt...
call .venv\Scripts\pip.exe install -r Core\requirements.txt
if errorlevel 1 (
    color 0c
    echo [ERROR] Gagal menginstall dependensi! Periksa koneksi internet Anda.
    pause
    exit /b 1
)
echo [OK] Virtual Environment berhasil dikonfigurasi!
goto :SET_PYTHON

:CHECK_DEPENDENCIES
:: Pengecekan cepat dependensi (<0.2 detik) tanpa tanda kurung di echo
.venv\Scripts\python.exe -c "import flask, requests, eth_account, eth_utils, PIL, qrcode" >nul 2>&1
if errorlevel 1 (
    echo [*] Mendeteksi modul baru atau pustaka yang belum terpasang.
    echo [*] Menjalankan instalasi/pembaruan dari Core\requirements.txt...
    call .venv\Scripts\pip.exe install -r Core\requirements.txt
)

:SET_PYTHON
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: ======================================================================
:: 3. Deteksi PM2 & Node.js
:: ======================================================================
set PM2_CMD=pm2
where pm2 >nul 2>&1
if errorlevel 1 (
    if exist "%APPDATA%\npm\pm2.cmd" (
        set PM2_CMD="%APPDATA%\npm\pm2.cmd"
    ) else if exist "C:\Program Files\nodejs\npm.cmd" (
        echo [*] Menginstall PM2 Process Manager secara global...
        call "C:\Program Files\nodejs\npm.cmd" install -g pm2 pm2-windows-startup
        set PM2_CMD="%APPDATA%\npm\pm2.cmd"
    )
)

:MENU
cd /d "%~dp0"
cls
echo ======================================================================
echo     BITGET WALLET TOOLS - ALL IN ONE CONTROLLER (TRIO MERAK)
echo ======================================================================
echo  [*] Port Web API : Port 2000 (LAN / Cloudflare topnodtools.web.id)
echo  [*] Mode PM2     : Terisolasi [bitget-server]
echo ======================================================================
echo.
echo Pilih Menu Operasi:
echo.
echo   [1] GAS WD XLM BITGET (Jalankan menu.py)
echo   [2] GAS BOT QRIS MORPH L2 (Jalankan qris_morph.py)
echo   [3] GAS WEB DASHBOARD CONTROLLER (Jalankan web_launcher.py)
echo   [4] BUKA SCRCPY (MIRRORING LAYAR HP)
echo   [5] JALANKAN SERVER BACKGROUND DENGAN PM2 (bitget-server)
echo   [6] LIHAT STATUS ^& LOG PM2 (pm2 status / logs bitget-server)
echo   [7] RESTART / STOP LAYANAN PM2 (Isolasi khusus bitget-server)
echo   [8] RESET ^& RESTART ADB SERVER (Kill ADB ^& Scrcpy)
echo   [9] PERIKSA / UPDATE DEPENDENSI PYTHON (pip install)
echo   [0] KELUAR
echo.
echo ======================================================================

choice /c 1234567890 /n /m "Pilihan Anda (0-9) [Default=1]: "
if errorlevel 10 exit
if errorlevel 9 goto UPDATE_REQUIREMENTS
if errorlevel 8 goto RESET_ADB
if errorlevel 7 goto CONTROL_PM2
if errorlevel 6 goto LOGS_PM2
if errorlevel 5 goto START_PM2
if errorlevel 4 goto RUN_SCRCPY
if errorlevel 3 goto RUN_DASHBOARD
if errorlevel 2 goto RUN_QRIS
if errorlevel 1 goto RUN_WD

goto MENU

:: ======================================================================
:: 1. GAS WD XLM
:: ======================================================================
:RUN_WD
cls
echo ======================================================================
echo            MENJALANKAN MENU UTAMA BOT AUTO WD XLM BITGET
echo ======================================================================
echo.
"%PYTHON_EXE%" Core\Python\menu.py
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, 'Core/Python'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" >nul 2>&1
echo.
echo ======================================================================
echo Tekan sembarang tombol untuk kembali ke menu utama...
pause >nul
goto MENU

:: ======================================================================
:: 2. GAS BOT QRIS MORPH L2
:: ======================================================================
:RUN_QRIS
cls
echo ======================================================================
echo             MENJALANKAN BOT ADB BITGET WALLET QRIS MORPH
echo ======================================================================
echo.
"%PYTHON_EXE%" Core\Python\qris_morph.py
"%PYTHON_EXE%" -c "import sys; sys.path.insert(0, 'Core/Python'); from screen_manager import restore_recorded_screen; restore_recorded_screen(silent=True)" >nul 2>&1
echo.
echo ======================================================================
echo Tekan sembarang tombol untuk kembali ke menu utama...
pause >nul
goto MENU

:: ======================================================================
:: 3. GAS WEB DASHBOARD CONTROLLER
:: ======================================================================
:RUN_DASHBOARD
cls
echo ======================================================================
echo       MENJALANKAN WEB DASHBOARD CONTROLLER INTERAKTIF (PORT 2000)
echo ======================================================================
echo.
"%PYTHON_EXE%" Core\Python\web_launcher.py
echo.
echo ======================================================================
echo Tekan sembarang tombol untuk kembali ke menu utama...
pause >nul
goto MENU

:: ======================================================================
:: 4. BUKA SCRCPY MIRRORING LAYAR HP
:: ======================================================================
:RUN_SCRCPY
cls
echo ======================================================================
echo              MEMBUKA SCRCPY MIRRORING LAYAR HP (120 FPS)
echo ======================================================================
echo.
if exist "Core\Python\scrcpy_launcher.py" (
    "%PYTHON_EXE%" Core\Python\scrcpy_launcher.py
) else if exist "Core\scrcpy-win64-v3.3.4\scrcpy.exe" (
    start "" "Core\scrcpy-win64-v3.3.4\scrcpy.exe" --tcpip
)
echo.
echo ======================================================================
echo Tekan sembarang tombol untuk kembali ke menu utama...
pause >nul
goto MENU

:: ======================================================================
:: 5. START PM2 BACKGROUND
:: ======================================================================
:START_PM2
cls
echo ======================================================================
echo     MENJALANKAN SERVER BACKGROUND DENGAN PM2 (bitget-server)
echo ======================================================================
echo.
echo [*] Menghapus instance lama bitget-server jika ada...
call %PM2_CMD% delete bitget-server >nul 2>&1
echo [*] Memulai bitget-server terisolasi...
call %PM2_CMD% start Core\ecosystem.config.js --only bitget-server
echo [*] Menyimpan status PM2...
call %PM2_CMD% save >nul 2>&1
echo.
echo [SUKSES] Service bitget-server aktif berjalan di latar belakang!
echo.
pause
goto MENU

:: ======================================================================
:: 6. STATUS & LOGS PM2
:: ======================================================================
:LOGS_PM2
cls
echo ======================================================================
echo                  STATUS & LOG PM2 [bitget-server]
echo ======================================================================
echo.
call %PM2_CMD% status
echo.
echo [Log Realtime - Tekan Ctrl+C untuk kembali ke menu]:
call %PM2_CMD% logs bitget-server --lines 30
pause
goto MENU

:: ======================================================================
:: 7. RESTART / STOP PM2 (TERISOLASI)
:: ======================================================================
:CONTROL_PM2
cls
echo ======================================================================
echo              KONTROL SERVICE PM2 TERISOLASI [bitget-server]
echo ======================================================================
echo.
echo   [1] RESTART bitget-server
echo   [2] STOP bitget-server
echo   [0] KEMBALI KE MENU UTAMA
echo.
choice /c 120 /n /m "Pilih tindakan (1/2/0): "
if errorlevel 3 goto MENU
if errorlevel 2 (
    echo.
    echo [*] Menghentikan service bitget-server...
    call %PM2_CMD% stop bitget-server
    pause
    goto MENU
)
if errorlevel 1 (
    echo.
    echo [*] Merestart service bitget-server...
    call %PM2_CMD% restart bitget-server --update-env
    pause
    goto MENU
)
goto MENU

:: ======================================================================
:: 8. RESET & RESTART ADB SERVER
:: ======================================================================
:RESET_ADB
cls
echo ======================================================================
echo                 RESET & RESTART ADB SERVER RESMI
echo ======================================================================
echo.
echo [*] Menghentikan proses adb, scrcpy, dan emulator...
taskkill /F /T /IM adb.exe /IM scrcpy.exe /IM scrcpy-noconsole.exe /IM QtScrcpy.exe /IM anlink.exe >nul 2>&1

echo [*] Memeriksa & membebaskan Port 5037 dan 5555...
for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /r ":5037.*LISTENING :5555.*LISTENING"') do (
    if "%%a" neq "0" if "%%a" neq "4" (
        taskkill /F /PID %%a /T >nul 2>&1
    )
)

if exist "Core\scrcpy-win64-v3.3.4\adb.exe" (
    set "ADB_BIN=Core\scrcpy-win64-v3.3.4\adb.exe"
) else (
    set "ADB_BIN=adb"
)

"%ADB_BIN%" kill-server >nul 2>&1
"%ADB_BIN%" forward --remove-all >nul 2>&1
"%ADB_BIN%" reverse --remove-all >nul 2>&1
"%ADB_BIN%" start-server >nul 2>&1

echo.
echo [+] Status Daemon ADB: BERHASIL DIMURNIKAN!
echo ----------------------------------------------------------------------
"%ADB_BIN%" devices -l
echo ----------------------------------------------------------------------
echo.
pause
goto MENU

:: ======================================================================
:: 9. UPDATE DEPENDENSI
:: ======================================================================
:UPDATE_REQUIREMENTS
cls
echo ======================================================================
echo             PEMBARUAN DEPENDENSI DARI Core\requirements.txt
echo ======================================================================
echo.
call .venv\Scripts\pip.exe install --upgrade -r Core\requirements.txt
echo.
echo [+] Selesai memeriksa & memperbarui pustaka!
pause
goto MENU
