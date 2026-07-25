import subprocess
import time

# Gunakan perintah adb global (telah di-inject oleh menu.py)
ADB_PATH = "adb"

def adb_command(command):
    subprocess.run(f'"{ADB_PATH}" {command}', shell=True)

def main():
    print("=========================================================")
    print("                  TESTER & RECORDER BOT                  ")
    print("=========================================================")
    print("CARA KERJA:")
    print("1. Script akan menjalankan 1 aksi ADB ke layar Anda.")
    print("2. Stopwatch (timer) akan langsung berjalan.")
    print("3. Anda perhatikan layar HP/Emulator Anda.")
    print("4. SAAT LAYAR SUDAH SIAP (loading selesai), langsung tekan tombol ENTER!")
    print("5. Waktu tunggu Anda akan dicatat otomatis menjadi 'jeda' yang pas.")
    print("=========================================================\n")
    
    input("Tekan ENTER untuk memulai eksekusi Langkah 1...")
    
    steps = [
        {"desc": "0. Scroll layar Multi App (Swipe Up)", "cmd": "shell input swipe 546 820 546 500 1000"},
        {"desc": "1. KLIK BITGET (Masuk dari Multi App)", "cmd": "shell input tap 164 423"},
        {"desc": "2. Klik Dompet 1", "cmd": "shell input tap 908 2258"},
        {"desc": "2. Klik Dompet 2", "cmd": "shell input tap 908 2258"},
        {"desc": "2.1 Swipe bawah (tutup popup default)", "cmd": "shell input swipe 560 1630 580 2377 300"},
        {"desc": "3. Klik Hadiah", "cmd": "shell input tap 212 816"},
        {"desc": "4. Klik XLM", "cmd": "shell input tap 536 1316"},
        {"desc": "5. Klik Penarikan", "cmd": "shell input tap 533 2302"},
        {"desc": "6. Klik Alamat Tujuan", "cmd": "shell input tap 525 631"},
        {"desc": "6.1 Input Alamat WD", "cmd": "shell input text 'GAEL2XQRRNPV2TCCFJFHHP277MN3MXUU2EZMRXRQBDVIUZLLODVH2SS5'"},
        {"desc": "7. Klik Semua (Max Amount)", "cmd": "shell input tap 969 888"},
        {"desc": "8. Klik area kosong (Tutup keyboard)", "cmd": "shell input tap 518 1452"},
        {"desc": "9. Klik Konfirmasi", "cmd": "shell input tap 541 2307"},
        {"desc": "10. Klik Konfirmasi Lagi (Modal)", "cmd": "shell input tap 800 2156"},
        {"desc": "11. Klik Selanjutnya (Ikat Google Auth)", "cmd": "shell input tap 530 2307"},
        {"desc": "12. Klik Copy Kode", "cmd": "shell input tap 982 1106"},
        {"desc": "13. Klik Selanjutnya", "cmd": "shell input tap 531 1676"},
        {"desc": "14. Buka Google Authenticator", "cmd": "shell monkey -p com.google.android.apps.authenticator2 -c android.intent.category.LAUNCHER 1"},
        {"desc": "15. Klik Tambah Kode (+)", "cmd": "shell input tap 985 2287"},
        {"desc": "16. Klik Masukkan Kunci Penyiapan", "cmd": "shell input tap 963 2066"},
        {"desc": "17. Klik Nama Kode", "cmd": "shell input tap 166 320"},
        {"desc": "17.1 Input Nomor Urut", "cmd": "shell input text '51'"},
        {"desc": "18. Klik Kunci Anda", "cmd": "shell input tap 338 508"},
        {"desc": "18.1 Paste Kode", "cmd": "shell input keyevent 279"},
        {"desc": "19. Tekan Back (Tutup Keyboard)", "cmd": "shell input keyevent 4"},
        {"desc": "20. Klik Tambahkan", "cmd": "shell input tap 536 2279"},
        {"desc": "21. Klik Tutup (Secure Screen)", "cmd": "shell input tap 983 2256"},
        {"desc": "22. Scroll mentok ke bawah 1", "cmd": "shell input swipe 525 2140 556 220 1000"},
        {"desc": "22.1 Scroll mentok ke bawah 2", "cmd": "shell input swipe 525 2140 556 220 1000"},
        {"desc": "23. Klik Code OTP untuk dicopy", "cmd": "shell input tap 535 2285"},
        {"desc": "24. Buka Recent Apps", "cmd": "shell input keyevent 187"},
        {"desc": "25. Klik Bitget Wallet (Kembali ke app)", "cmd": "shell input tap 851 1329"},
        {"desc": "26. Klik Tempel OTP", "cmd": "shell input tap 920 426"},
        {"desc": "27. Klik Ikat", "cmd": "shell input tap 525 2310"},
        {"desc": "28. Klik area kosong (Ganti metode ke PIN)", "cmd": "shell input tap 528 1270"},
        {"desc": "29. Klik Beralih ke sandi/pin", "cmd": "shell input tap 546 2302"},
        {"desc": "30. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "30. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "30. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "30. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "30. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "30. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "31. Klik Konfirmasi (Halaman WD)", "cmd": "shell input tap 536 2302"},
        {"desc": "32. Klik Tempel (di Otentikasi Google)", "cmd": "shell input tap 946 2027"},
        {"desc": "33. Klik Otentikasi", "cmd": "shell input tap 797 2233"},
        {"desc": "34. Klik area kosong (Ganti metode ke PIN lagi)", "cmd": "shell input tap 495 1093"},
        {"desc": "35. Klik Beralih ke sandi/pin", "cmd": "shell input tap 531 2302"},
        {"desc": "36. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "36. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "36. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "36. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "36. Input PIN 080808 - Tap 0", "cmd": "shell input tap 546 2258"},
        {"desc": "36. Input PIN 080808 - Tap 8", "cmd": "shell input tap 546 2127"},
        {"desc": "37. Klik Oke", "cmd": "shell input tap 533 2310"},
        {"desc": "38. Tekan Back 1", "cmd": "shell input keyevent 4"},
        {"desc": "38. Tekan Back 2", "cmd": "shell input keyevent 4"},
        {"desc": "38. Tekan Back 3", "cmd": "shell input keyevent 4"},
        {"desc": "38. Tekan Back 4", "cmd": "shell input keyevent 4"},
        {"desc": "38. Tekan Back 5 (Ke Home)", "cmd": "shell input keyevent 4"},
        {"desc": "39. Klik Buka Multi App", "cmd": "shell input tap 135 500"},
        {"desc": "40. Klik Titik Tiga (Menu Multi App)", "cmd": "shell input tap 1032 145"},
        {"desc": "41. Klik Kill All Apps", "cmd": "shell input tap 773 273"},
        {"desc": "42. Klik Confirm (Kill All Apps)", "cmd": "shell input tap 846 1284"}
    ]

    recorded_delays = []

    for step in steps:
        print(f"\n[EKSEKUSI] {step['desc']}")
        adb_command(step['cmd'])
        
        # Mulai hitung waktu (Stopwatch)
        start_time = time.time()
        
        # Tunggu user menekan enter
        input(">>> Tekan ENTER jika layar SUDAH BERUBAH/SIAP untuk langkah berikutnya...")
        
        end_time = time.time()
        elapsed = round(end_time - start_time, 2)
        print(f"--> [TERCATAT] Jeda yang dibutuhkan: {elapsed} detik")
        
        recorded_delays.append({"desc": step["desc"], "delay": elapsed})
        
    print("\n=================================================")
    print("         REKAP JEDA (SLEEP) YANG TERCATAT        ")
    print("=================================================")
    for record in recorded_delays:
        print(f"jeda={record['delay']}s  -->  {record['desc']}")
    
    print("\nSelesai! Anda bisa menyalin rekap jeda di atas ke dalam file wd_xlm.py")

if __name__ == "__main__":
    main()
