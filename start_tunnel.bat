@echo off
color 0B
echo =========================================================
echo       KONEKSI ADB LOKAL KE VPS (REVERSE SSH TUNNEL)       
echo =========================================================
echo Script ini akan meneruskan koneksi USB HP Anda ke VPS
echo sehingga Web Dashboard di VPS bisa mengendalikan emulator.
echo.
echo Pastikan Anda sudah mengubah IP_VPS dan USER_VPS di dalam
echo script ini (klik kanan - edit) sesuai dengan VPS Anda!
echo.
pause

:: ========================================
:: UBAH BAGIAN INI SESUAI DENGAN VPS ANDA
:: ========================================
set IP_VPS=123.45.67.89
set USER_VPS=root
:: ========================================

echo.
echo [1] Menghentikan server ADB lokal...
C:\Users\fajar\Downloads\php\libraries\adb.exe kill-server

echo [2] Memulai server ADB agar siap menerima koneksi eksternal...
start /b C:\Users\fajar\Downloads\php\libraries\adb.exe -a nodaemon server start

echo [3] Membuka terowongan SSH ke %IP_VPS%...
echo Silakan masukkan password VPS Anda jika diminta!
ssh -R 5037:127.0.0.1:5037 %USER_VPS%@%IP_VPS%

pause
