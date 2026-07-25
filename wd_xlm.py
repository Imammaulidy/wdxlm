import subprocess
import time
import os
import platform
import sys
import json

if platform.system() == "Windows":
    import msvcrt

def stoppable_sleep(jeda):
    """Tunggu selama 'jeda' detik. Jika di Windows dan ENTER ditekan, hentikan script seketika."""
    end_time = time.time() + jeda
    while time.time() < end_time:
        if platform.system() == "Windows":
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'\r', b'\n'):
                    print("\n\n[!!!] EKSEKUSI DIHENTIKAN PAKSA OLEH PENGGUNA (TOMBOL ENTER DITEKAN) [!!!]")
                    sys.exit(0)
        time.sleep(0.05)

# Gunakan perintah adb global (telah di-inject oleh menu.py)
ADB_PATH = "adb"

def adb_command(command):
    """Menjalankan perintah ADB dan mengembalikan outputnya."""
    # VPS akan membaca env var ADB_SERVER_SOCKET jika ada saat dieksekusi oleh subprocess
    try:
        result = subprocess.run(f'"{ADB_PATH}" {command}' if platform.system() == "Windows" else f'{ADB_PATH} {command}', shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error executing ADB command: {e}")
        return ""

def tap(x, y, jeda=1.0):
    """Simulasi klik (tap) pada layar di koordinat (x, y)."""
    print(f"Tapping at ({x}, {y}) - Waiting {jeda}s")
    adb_command(f"shell input tap {x} {y}")
    stoppable_sleep(jeda)

def swipe(x1, y1, x2, y2, duration=500, jeda=1.0):
    """Simulasi geser (swipe) pada layar."""
    print(f"Swiping from ({x1}, {y1}) to ({x2}, {y2}) - Waiting {jeda}s")
    adb_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    stoppable_sleep(jeda)

def input_text(text, jeda=1.0):
    """Input teks ke dalam kolom yang sedang aktif."""
    print(f"Typing text: {text}")
    text = str(text).replace(' ', '%s')
    adb_command(f"shell input text '{text}'")
    stoppable_sleep(jeda)

def paste_clipboard(jeda=1.0):
    """Mensimulasikan aksi Paste (Tempel) dari clipboard bawaan Android."""
    print(f"Pasting from clipboard - Waiting {jeda}s")
    # KEYCODE_PASTE = 279
    adb_command("shell input keyevent 279")
    stoppable_sleep(jeda)

def press_back(jeda=1.0):
    """Mensimulasikan tombol Back sistem."""
    print(f"Pressing BACK - Waiting {jeda}s")
    adb_command("shell input keyevent 4")
    stoppable_sleep(jeda)
    
def open_recent_apps(jeda=2.0):
    """Membuka layar Recent Apps."""
    print(f"Opening Recent Apps - Waiting {jeda}s")
    # KEYCODE_APP_SWITCH = 187
    adb_command("shell input keyevent 187")
    stoppable_sleep(jeda)

def tap_dynamic_pin(pin_str, keypad_coords, final_jeda=5.0):
    """Melakukan ketikan PIN secara dinamis menggunakan mapping koordinat."""
    print(f"Memasukkan PIN dinamis via kordinat sentuh...")
    for i, digit in enumerate(pin_str):
        if digit in keypad_coords:
            coord = keypad_coords[digit]
            # Jika ini digit terakhir, gunakan final_jeda
            jeda_to_use = final_jeda if i == len(pin_str) - 1 else 0.35
            tap(coord["x"], coord["y"], jeda=jeda_to_use)
        else:
            print(f"Peringatan: Koordinat untuk angka {digit} tidak ditemukan!")

def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Gagal memuat config.json: {e}")
        sys.exit(1)

def main():
    config = load_config()
    print("Starting Bitget Wallet XLM Withdrawal Script...")
    
    # 1. Pastikan device terkoneksi
    devices = adb_command("devices")
    if "device" not in devices:
        print("Device tidak ditemukan! Pastikan sudah terkoneksi via USB.")
        sys.exit()
    print(f"Connected devices:\n{devices}")
    
    # Konfigurasi Looping
    TOTAL_AKUN = config.get("total_akun", 5)
    ALAMAT_WD = config.get("alamat_wd", "")
    PIN = config.get("pin", "080808")
    KEYPAD = config.get("keypad_coords", {})
    
    # Nomor Urut Awal untuk Penamaan di Google Authenticator
    START_INDEX = config.get("start_index", 51) 
    
    for i in range(TOTAL_AKUN):
        current_account_num = START_INDEX + i
        print(f"\n========== MEMPROSES AKUN KE-{current_account_num} ==========")
        
        # 0. Scroll layar Multi App agar clone berikutnya naik ke atas
        print("Menggeser layar Multi App Ultra...")
        swipe(546, 820, 546, 500, duration=1000, jeda=1.0)
        
        # 1. KLIK BITGET (Buka clone aplikasi dari Multi App)
        tap(164, 423, jeda=6.6)
        
        # 2. Klik Dompet (Klik 2 kali)
        tap(908, 2258, jeda=1.8)
        tap(908, 2258, jeda=1.6)
        
        # 2.1 Swipe bawah (tutup popup default jika muncul)
        print("Swipe bawah (menutup popup jika ada)...")
        swipe(560, 1630, 580, 2377, duration=300, jeda=2.3)
        
        # 3. Klik Hadiah
        tap(212, 816, jeda=3.2)
        
        # 4. Klik XLM
        tap(536, 1316, jeda=2.4)
        
        # 5. Klik Penarikan
        tap(533, 2302, jeda=1.9)
        
        # 6. Klik Alamat Tujuan
        tap(525, 631, jeda=0.8)
        # Isikan Alamat
        input_text(ALAMAT_WD, jeda=1.7)
        
        # 7. Klik Semua (Max Amount)
        tap(969, 888, jeda=1.6)
        
        # 8. Klik area kosong untuk menghilangkan keyboard
        tap(518, 1452, jeda=1.3)
        
        # 9. Klik Konfirmasi
        tap(541, 2307, jeda=1.2)
        
        # 10. Klik Konfirmasi Lagi (Modal Pengingat)
        tap(800, 2156, jeda=1.2)
        
        # 11. Klik Selanjutnya (Halaman Ikat Google Auth)
        tap(530, 2307, jeda=2.4)
        
        # 12. Klik Copy Kode
        tap(982, 1106, jeda=1.0)
        
        # 13. Klik Selanjutnya
        tap(531, 1676, jeda=1.2)
        
        # 14. Buka Google Authenticator
        print("Membuka Google Authenticator...")
        adb_command("shell monkey -p com.google.android.apps.authenticator2 -c android.intent.category.LAUNCHER 1")
        stoppable_sleep(2.5)
        
        # 15. Klik Tambah Kode (+) di Google Auth
        tap(985, 2287, jeda=1.4)
        
        # 16. Klik Masukkan Kunci Penyiapan (Enter a setup key)
        tap(963, 2066, jeda=1.2)
        
        # 17. Klik Nama Kode dan Masukkan Nomor Urut Otomatis
        tap(166, 320, jeda=1.0)
        input_text(str(current_account_num), jeda=0.8)
        
        # 18. Klik Kunci Anda dan Paste Kode
        tap(338, 508, jeda=1.0)
        paste_clipboard(jeda=1.1)
        
        # 19. Pencet Back untuk menutup keyboard
        press_back(jeda=0.9)
        
        # 20. Klik Tambahkan
        tap(536, 2279, jeda=2.1)
        
        # 21. Klik Tutup (Berdasarkan koordinat karena layar blank/secure)
        tap(983, 2256, jeda=1.0)
        
        # 22. Scroll ke bawah mentok (Diulang 2 kali)
        swipe(525, 2140, 556, 220, duration=1000, jeda=0.6)
        swipe(525, 2140, 556, 220, duration=1000, jeda=0.4)
            
        # 23. Klik Code OTP di paling bawah untuk meng-copy-nya
        tap(535, 2285, jeda=1.0)
        
        # 24. Buka Recent Apps
        open_recent_apps(jeda=0.9)
        
        # 25. Klik Bitget Wallet di sebelah kanan
        tap(851, 1329, jeda=1.1)
        
        # 26. Klik tombol Tempel (di Bitget Wallet)
        tap(920, 426, jeda=0.6)
        
        # 27. Klik Ikat
        tap(525, 2310, jeda=1.2)
        
        # 28. Klik area kosong (agar ganti metode FP ke PIN)
        tap(528, 1270, jeda=1.1)
        
        # 29. Klik Beralih ke sandi/pin
        tap(546, 2302, jeda=0.9)
        
        # 30. Masukkan PIN dinamis via sentuhan layar
        tap_dynamic_pin(PIN, KEYPAD, final_jeda=2.5)
        
        # 31. Klik Konfirmasi (setelah kembali ke halaman WD)
        tap(536, 2302, jeda=0.9)
        
        # 32. Klik Tempel (di modal Otentikasi Google)
        tap(946, 2027, jeda=0.4)
        
        # 33. Klik Otentikasi
        tap(797, 2233, jeda=1.2)
        
        # 34. Klik area kosong (Ganti metode)
        tap(495, 1093, jeda=1.0)
        
        # 35. Klik Beralih ke sandi/pin
        tap(531, 2302, jeda=0.9)
        
        # 36. Masukkan PIN dinamis lagi
        tap_dynamic_pin(PIN, KEYPAD, final_jeda=4.0)
        
        # 37. Klik Oke (Hasil penarikan dikirim)
        tap(533, 2310, jeda=1.9)
        
        # ==========================================
        # KEMBALI KE MULTI APP
        # ==========================================
        print("Proses berhasil, menekan BACK untuk keluar ke Home...")
        # 38. Lakukan back 5 kali untuk memastikan keluar sampai Home
        for _ in range(5):
            press_back(jeda=0.7)
        
        # 39. Buka kembali Multi App Ultra dari Home
        tap(135, 500, jeda=1.5)
        
        # 40. Klik Titik Tiga (Menu Multi App)
        tap(1032, 145, jeda=0.6)
        
        # 41. Klik Kill All Apps
        tap(773, 273, jeda=0.9)
        
        # 42. Klik Confirm (Kill All Apps)
        tap(846, 1284, jeda=5.5)
        
    print("\nSemua akun selesai diproses.")

if __name__ == "__main__":
    main()
