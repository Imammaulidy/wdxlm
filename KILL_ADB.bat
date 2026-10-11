@echo off
title SUPER POWER ADB ^& MIRRORING PROCESS KILLER
cd /d "%~dp0"
color 0C

:: ----------------------------------------------------------------------
:: 1. VERIFIKASI HAK AKSES ADMINISTRATOR (SUPER POWER AUTO-ELEVATION)
:: ----------------------------------------------------------------------
if "%1"==":direct" goto :run_killer

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ======================================================================
    echo   [!] MEMBUTUHKAN HAK AKSES ADMINISTRATOR (SUPER POWER MODE)
    echo   [*] Meminta perizinan sistem Windows UAC...
    echo ======================================================================
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c %~s0 :direct' -Verb RunAs"
    exit /b
)

:run_killer
cls
echo ======================================================================
echo          SUPER POWER ADB ^& MIRRORING PROCESS KILLER
echo    PEMBERSIH TOTAL: ADB, SCRCPY, EMULATOR ^& THIRD-PARTY MIRROR
echo ======================================================================
echo.

:: Menentukan path resmi ADB dari project
if exist "%~dp0core\scrcpy-win64-v3.3.4\adb.exe" (
    set "ADB_BIN=%~dp0core\scrcpy-win64-v3.3.4\adb.exe"
) else (
    set "ADB_BIN=adb"
)

echo [*] Mengidentifikasi hak akses sistem...
net session >nul 2>&1
if %errorlevel% equ 0 (
    echo  [+] Hak Akses: ADMINISTRATOR (SUPER POWER AKTIF)
) else (
    echo  [!] Hak Akses: STANDARD USER
)
echo.

:: ----------------------------------------------------------------------
:: 2. PEMUSNAHAN DAFTAR PROSES MIRRORING & ADB PIHAK KETIGA
:: ----------------------------------------------------------------------
echo [*] [STEP 1/4] Menghentikan semua aplikasi Mirroring ^& ADB yang terkunci...

set "TARGET_LIST=adb.exe scrcpy.exe scrcpy-noconsole.exe QtScrcpy.exe QtScrcpy-noconsole.exe anlink.exe Anlink.exe AnlinkServer.exe vysor.exe Vysor.exe apowermirror.exe ApowerMirror.exe Apowersoft.CommUtilities.exe ApowerManager.exe apowersoft.exe TotalControl.exe tcserver.exe TC.exe TCMain.exe MirrorGo.exe WSDownloader.exe Mobizen.exe PandaActivator.exe PandaGamepad.exe nox_adb.exe Nox.exe ld_adb.exe dnplayer.exe HD-Adb.exe HD-Player.exe MEmuConsole.exe MEmu.exe MEmuHeadless.exe MuMuPlayer.exe"

for %%p in (%TARGET_LIST%) do (
    taskkill /F /T /IM %%p >nul 2>&1
    wmic process where "name='%%p'" call terminate >nul 2>&1
)

:: Sapu bersih tambahan via PowerShell
powershell -NoProfile -Command "$procs = @('adb','scrcpy','scrcpy-noconsole','QtScrcpy','anlink','AnlinkServer','vysor','apowermirror','Apowersoft.CommUtilities','ApowerManager','TotalControl','tcserver','MirrorGo','Mobizen','PandaActivator','nox_adb','ld_adb','HD-Adb','MEmuConsole','dnplayer'); Get-Process -Name $procs -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1

echo  [+] Semua proses target berhasil dihentikan.
echo.

:: ----------------------------------------------------------------------
:: 3. PORT 5037 & 5555 HOSTAGE HUNTER (BRUTEFORCE KILL BY PORT LISTENER)
:: ----------------------------------------------------------------------
echo [*] [STEP 2/4] Memeriksa penyanderaan Port 5037 (ADB) dan 5555 (Wi-Fi)...

for /f "tokens=5" %%a in ('netstat -ano -p tcp ^| findstr /r ":5037.*LISTENING :5555.*LISTENING"') do (
    if "%%a" neq "0" if "%%a" neq "4" (
        echo  [-] Membebaskan port dari PID sandera: %%a...
        taskkill /F /PID %%a /T >nul 2>&1
        wmic process where "ProcessId=%%a" call terminate >nul 2>&1
        powershell -NoProfile -Command "Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue" >nul 2>&1
    )
)

echo  [+] Port 5037 dan 5555 bebas ^& bersih.
echo.

:: ----------------------------------------------------------------------
:: 4. RESET TUNNEL ADB & FLUSH CACHE
:: ----------------------------------------------------------------------
echo [*] [STEP 3/4] Me-reset Forwarding Tunnel ^& Cache ADB...
ping 127.0.0.1 -n 2 >nul

"%ADB_BIN%" kill-server >nul 2>&1
"%ADB_BIN%" forward --remove-all >nul 2>&1
"%ADB_BIN%" reverse --remove-all >nul 2>&1

echo  [+] Tunnel ADB berhasil di-reset.
echo.

:: ----------------------------------------------------------------------
:: 5. RESTART SERVER RESMI ADB & DETEKSI PERANGKAT
:: ----------------------------------------------------------------------
echo [*] [STEP 4/4] Menyalakan ulang Server ADB resmi project...
"%ADB_BIN%" start-server >nul 2>&1

color 0A
echo.
echo ======================================================================
echo    STATUS AKHIR: SERVER ADB BERHASIL DIMURNIKAN!
echo ======================================================================
echo.
echo Daftar Perangkat Android Terkoneksi:
echo ----------------------------------------------------------------------
"%ADB_BIN%" devices -l
echo ----------------------------------------------------------------------
echo.
echo [Petunjuk]:
echo  - Jika perangkat muncul status 'device'     : Siap digunakan di Dashboard!
echo  - Jika perangkat muncul status 'unauthorized': Buka HP, centang 'Selalu izinkan'
echo  - Jika perangkat kosong                      : Cabut ^& pasang kembali kabel USB
echo.
echo ======================================================================
echo Tekan tombol apa saja untuk menutup jendela ini...
pause >nul
