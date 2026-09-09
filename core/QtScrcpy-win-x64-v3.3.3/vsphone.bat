@echo off
title VSPhone ADB Auto-Connect
color 0A

:: ==========================================
:: KONFIGURASI VSPHONE (Edit Port & Password jika berubah)
:: ==========================================
set PORT=54819
set SSH_HOST=103.237.100.130
set SSH_PORT=1824
set SSH_USER=s
set PASSWORD=VOmY65kGx78cUkxOObQuI/fv8JcAPu4khItv/IjXe8m6zodtbAoau86IEws9S4w3BYdze7TbG4OCDmCVf8wm3y/SX19Fm+2y46796flLmazNQRhUCVQkMBCaE6cWbLij58iAPhmGjCUZrLK9p5kJJhs8Ye8i42ZgaW0e5qDWqut+7E5C16uh9u5bDVBtJiStJ1A6FGKfnIPFc8Sipsuwk0q7sh2UhdxhwOyYcpCeZU7b

echo ===================================================
echo     MEMULAI KONEKSI VSPHONE (PORT %PORT%)
echo ===================================================
echo.

:: 1. Copy Password ke Clipboard
<nul set /p="%PASSWORD%" | clip
echo [INFO] Password sudah di-COPY otomatis!
echo.
echo [TIPS PENTING]: 
echo Saat muncul tulisan "password:", silakan KLIK KANAN satu kali di area hitam ini, lalu tekan ENTER.
echo (Teks password memang TIDAK AKAN TERLIHAT saat di-paste, itu normal).
echo.

:: 2. Eksekusi SSH
echo Menghubungkan jalur SSH...
ssh -oStrictHostKeyChecking=accept-new %SSH_USER%@%SSH_HOST% -p %SSH_PORT% -L %PORT%:localhost:1 -Nf

:: Jeda 3 detik agar SSH stabil di latar belakang
timeout /t 3 /nobreak >nul
echo.

:: 3. Eksekusi ADB
echo Menghubungkan ADB ke localhost:%PORT%...
adb connect localhost:%PORT%

echo.
echo ===================================================
echo KONEKSI SUKSES! Silakan buka QtScrcpy.
echo ===================================================
echo.
echo JANGAN TUTUP JENDELA INI SEBELUM SELESAI.
echo Tekan tombol ENTER pada keyboard jika sudah selesai untuk memutus koneksi...
pause >nul

:: 4. Eksekusi Kill (Membersihkan ADB dan SSH)
echo.
echo Sedang menutup koneksi ADB dan SSH...
adb kill-server
taskkill /F /IM ssh.exe >nul 2>&1

echo.
echo Koneksi berhasil diputus. Sampai jumpa!
timeout /t 2 >nul