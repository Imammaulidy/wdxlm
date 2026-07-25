import subprocess
import time
import os
import platform
import sys
import json

if platform.system() == "Windows":
    import msvcrt

current_step_info = "Menyiapkan bot..."

def log_step(text):
    global current_step_info
    current_step_info = text
    print(f"\n---> {text}")

def stoppable_sleep(jeda):
    """Tunggu selama 'jeda' detik. Jika di Windows dan ENTER ditekan, PAUSE script."""
    end_time = time.time() + jeda
    while time.time() < end_time:
        paused = False
        if platform.system() == "Windows":
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b'\r', b'\n'):
                    paused = True
        else:
            import select
            i, o, e = select.select([sys.stdin], [], [], 0)
            if i:
                sys.stdin.readline() # consume the input
                paused = True
                
        if paused:
            sisa_waktu = end_time - time.time()
            print("\n\n[!!!] PROGRAM DIPAUSE (TOMBOL ENTER DITEKAN) [!!!]")
            print(f"[*] POSISI TERAKHIR: {current_step_info}")
            print("Silakan perbaiki posisi layar HP Anda agar sesuai dengan langkah di atas.")
            print(" --> Tekan ENTER lagi untuk MELANJUTKAN")
            print(" --> Ketik 'Q' lalu ENTER untuk BERHENTI TOTAL")
            while True:
                if platform.system() == "Windows":
                    resume_key = msvcrt.getch()
                    if resume_key in (b'\r', b'\n'):
                        break
                    elif resume_key in (b'q', b'Q', b'x', b'X'):
                        print("\n[X] EKSEKUSI DIHENTIKAN PAKSA OLEH PENGGUNA.")
                        sys.exit(0)
                else:
                    import select
                    i, o, e = select.select([sys.stdin], [], [], 0.1)
                    if i:
                        resume_key = sys.stdin.readline().strip().lower()
                        if resume_key in ('q', 'x'):
                            print("\n[X] EKSEKUSI DIHENTIKAN PAKSA OLEH PENGGUNA.")
                            sys.exit(0)
                        else:
                            break
            
            print("\n[>] MELANJUTKAN PROSES...\n")
            end_time = time.time() + sisa_waktu
            
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

def auto_detect_clone_number():
    """Menggunakan uiautomator untuk membaca nomor clone terdekat dari titik klik (Y=423)."""
    print("\n[*] (AI Pintar) Membaca layar untuk mencari nomor urut clone...")
    adb_command("shell uiautomator dump /data/local/tmp/ui.xml")
    xml_data = adb_command("shell cat /data/local/tmp/ui.xml")
    
    import re
    # Ekstrak semua teks yang hanya berisi angka dan ambil nilai Y atasnya
    matches = re.findall(r'text="(\d+)"(?:[^>]*?)bounds="\[\d+,(\d+)\]\[\d+,\d+\]"', xml_data)
    
    if matches:
        valid_matches = []
        for num_str, y_str in matches:
            num = int(num_str)
            y = int(y_str)
            # Filter angka logis dan hindari status bar (y < 100)
            if 1 <= num <= 9999 and y > 100:
                # Titik klik kita ada di Y=423, cari angka yang letaknya paling dekat dengan 423
                jarak = abs(y - 423)
                valid_matches.append((num, jarak))
        
        if valid_matches:
            # Urutkan dari yang jaraknya paling dekat
            valid_matches.sort(key=lambda x: x[1])
            best_match = valid_matches[0][0]
            print(f"[+] Berhasil! AI mendeteksi Anda akan mengklik Clone ke-{best_match}")
            return best_match
            
    print("[-] AI gagal mendeteksi nomor di layar. Menggunakan urutan default.")
    return None

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
    
    log_step("# 1. Pastikan device terkoneksi")
    
    # 1. Pastikan device terkoneksi
    devices = adb_command("devices")
    if "device" not in devices:
        print("Device tidak ditemukan! Pastikan sudah terkoneksi via USB.")
        sys.exit()
    print(f"Connected devices:\n{devices}")
    
    # Ambil perangkat pertama yang valid untuk menghindari error 'more than one device'
    valid_devices = [line.split()[0] for line in devices.splitlines() if 'device' in line and not line.startswith('List')]
    
    if len(valid_devices) > 1:
        print("\n[!] Ditemukan lebih dari 1 perangkat yang terkoneksi:")
        for idx, dev in enumerate(valid_devices):
            print(f"  {idx + 1}. {dev}")
        pilih = input(f"Ketik nomor perangkat yang ingin digunakan (1-{len(valid_devices)}): ").strip()
        try:
            pilih_idx = int(pilih) - 1
            if 0 <= pilih_idx < len(valid_devices):
                os.environ['ANDROID_SERIAL'] = valid_devices[pilih_idx]
                print(f"[*] Menargetkan perintah ADB ke perangkat: {valid_devices[pilih_idx]}\n")
            else:
                raise ValueError
        except:
            os.environ['ANDROID_SERIAL'] = valid_devices[0]
            print(f"[*] Pilihan tidak valid, menggunakan perangkat pertama: {valid_devices[0]}\n")
            
    elif valid_devices:
        os.environ['ANDROID_SERIAL'] = valid_devices[0]
        print(f"[*] Menargetkan perintah ADB ke perangkat: {valid_devices[0]}\n")
    
    # Konfigurasi Looping
    TOTAL_AKUN = config.get("total_akun", 5)
    ALAMAT_WD = config.get("alamat_wd", "")
    PIN = config.get("pin", "080808")
    KEYPAD = config.get("keypad_coords", {})
    
    # Nomor Urut Awal untuk Penamaan di Google Authenticator
    START_INDEX = config.get("start_index", 51) 
    
    for i in range(TOTAL_AKUN):
        log_step("# 0. Scroll layar Multi App agar clone berikutnya naik ke atas")
        
        # 0. Scroll layar Multi App agar clone berikutnya naik ke atas
        print("Menggeser layar Multi App Ultra...")
        swipe(546, 820, 546, 500, duration=1000, jeda=1.0)
        
        # --- AI PINTAR (Hanya di loop pertama) ---
        if i == 0:
            ai_number = auto_detect_clone_number()
            if ai_number is not None:
                START_INDEX = ai_number
                
        current_account_num = START_INDEX + i
        print(f"\n========== MEMPROSES AKUN KE-{current_account_num} ==========")
        
        log_step("# 1. KLIK BITGET (Buka clone aplikasi dari Multi App)")
        
        # 1. KLIK BITGET (Buka clone aplikasi dari Multi App)
        tap(164, 423, jeda=6.6)
        
        log_step("# 2. Klik Dompet (Klik 2 kali)")
        
        # 2. Klik Dompet (Klik 2 kali)
        tap(908, 2258, jeda=1.8)
        tap(908, 2258, jeda=1.6)
        
        log_step("# 2.1 Swipe bawah (tutup popup default jika muncul)")
        
        # 2.1 Swipe bawah (tutup popup default jika muncul)
        print("Swipe bawah (menutup popup jika ada)...")
        swipe(560, 1630, 580, 2377, duration=300, jeda=2.3)
        
        log_step("# 3. Klik Hadiah")
        
        # 3. Klik Hadiah
        tap(212, 816, jeda=3.2)
        
        log_step("# 4. Klik XLM")
        
        # 4. Klik XLM
        tap(536, 1316, jeda=2.4)
        
        log_step("# 5. Klik Penarikan")
        
        # 5. Klik Penarikan
        tap(533, 2302, jeda=1.9)
        
        log_step("# 6. Klik Alamat Tujuan")
        
        # 6. Klik Alamat Tujuan
        tap(525, 631, jeda=0.8)
        # Isikan Alamat
        input_text(ALAMAT_WD, jeda=1.7)
        
        log_step("# 7. Klik Semua (Max Amount)")
        
        # 7. Klik Semua (Max Amount)
        tap(969, 888, jeda=1.6)
        
        log_step("# 8. Klik area kosong untuk menghilangkan keyboard")
        
        # 8. Klik area kosong untuk menghilangkan keyboard
        tap(518, 1452, jeda=1.3)
        
        log_step("# 9. Klik Konfirmasi")
        
        # 9. Klik Konfirmasi
        tap(541, 2307, jeda=1.2)
        
        log_step("# 10. Klik Konfirmasi Lagi (Modal Pengingat)")
        
        # 10. Klik Konfirmasi Lagi (Modal Pengingat)
        tap(800, 2156, jeda=1.2)
        
        log_step("# 11. Klik Selanjutnya (Halaman Ikat Google Auth)")
        
        # 11. Klik Selanjutnya (Halaman Ikat Google Auth)
        tap(530, 2307, jeda=2.4)
        
        log_step("# 12. Klik Copy Kode")
        
        # 12. Klik Copy Kode
        tap(982, 1106, jeda=1.0)
        
        log_step("# 13. Klik Selanjutnya")
        
        # 13. Klik Selanjutnya
        tap(531, 1676, jeda=1.2)
        
        log_step("# 14. Buka Google Authenticator")
        
        # 14. Buka Google Authenticator
        print("Membuka Google Authenticator...")
        adb_command("shell monkey -p com.google.android.apps.authenticator2 -c android.intent.category.LAUNCHER 1")
        stoppable_sleep(2.5)
        
        log_step("# 15. Klik Tambah Kode (+) di Google Auth")
        
        # 15. Klik Tambah Kode (+) di Google Auth
        tap(985, 2287, jeda=1.4)
        
        log_step("# 16. Klik Masukkan Kunci Penyiapan (Enter a setup key)")
        
        # 16. Klik Masukkan Kunci Penyiapan (Enter a setup key)
        tap(963, 2066, jeda=1.2)
        
        log_step("# 17. Klik Nama Kode dan Masukkan Nomor Urut Otomatis")
        
        # 17. Klik Nama Kode dan Masukkan Nomor Urut Otomatis
        tap(166, 320, jeda=1.0)
        input_text(str(current_account_num), jeda=0.8)
        
        log_step("# 18. Klik Kunci Anda dan Paste Kode")
        
        # 18. Klik Kunci Anda dan Paste Kode
        tap(338, 508, jeda=1.0)
        paste_clipboard(jeda=1.1)
        
        log_step("# 19. Pencet Back untuk menutup keyboard")
        
        # 19. Pencet Back untuk menutup keyboard
        press_back(jeda=0.9)
        
        log_step("# 20. Klik Tambahkan")
        
        # 20. Klik Tambahkan
        tap(536, 2279, jeda=2.1)
        
        log_step("# 21. Klik Tutup (Berdasarkan koordinat karena layar blank/secure)")
        
        # 21. Klik Tutup (Berdasarkan koordinat karena layar blank/secure)
        tap(983, 2256, jeda=1.0)
        
        log_step("# 22. Scroll ke bawah mentok (Diulang 2 kali)")
        
        # 22. Scroll ke bawah mentok (Diulang 2 kali)
        swipe(525, 2140, 556, 220, duration=1000, jeda=0.6)
        swipe(525, 2140, 556, 220, duration=1000, jeda=0.4)
            
        log_step("# 23. Klik Code OTP di paling bawah untuk meng-copy-nya")
            
        # 23. Klik Code OTP di paling bawah untuk meng-copy-nya
        tap(535, 2285, jeda=1.0)
        
        log_step("# 24. Buka Recent Apps")
        
        # 24. Buka Recent Apps
        open_recent_apps(jeda=0.9)
        
        log_step("# 25. Klik Bitget Wallet di sebelah kanan")
        
        # 25. Klik Bitget Wallet di sebelah kanan
        tap(851, 1329, jeda=1.1)
        
        log_step("# 26. Klik tombol Tempel (di Bitget Wallet)")
        
        # 26. Klik tombol Tempel (di Bitget Wallet)
        tap(920, 426, jeda=0.6)
        
        log_step("# 27. Klik Ikat")
        
        # 27. Klik Ikat
        tap(525, 2310, jeda=1.2)
        
        log_step("# 28. Klik area kosong (agar ganti metode FP ke PIN)")
        
        # 28. Klik area kosong (agar ganti metode FP ke PIN)
        tap(528, 1270, jeda=1.1)
        
        log_step("# 29. Klik Beralih ke sandi/pin")
        
        # 29. Klik Beralih ke sandi/pin
        tap(546, 2302, jeda=0.9)
        
        log_step("# 30. Masukkan PIN dinamis via sentuhan layar")
        
        # 30. Masukkan PIN dinamis via sentuhan layar
        tap_dynamic_pin(PIN, KEYPAD, final_jeda=2.5)
        
        log_step("# 31. Klik Konfirmasi (setelah kembali ke halaman WD)")
        
        # 31. Klik Konfirmasi (setelah kembali ke halaman WD)
        tap(536, 2302, jeda=0.9)
        
        log_step("# 32. Klik Tempel (di modal Otentikasi Google)")
        
        # 32. Klik Tempel (di modal Otentikasi Google)
        tap(946, 2027, jeda=0.4)
        
        log_step("# 33. Klik Otentikasi")
        
        # 33. Klik Otentikasi
        tap(797, 2233, jeda=1.2)
        
        log_step("# 34. Klik area kosong (Ganti metode)")
        
        # 34. Klik area kosong (Ganti metode)
        tap(495, 1093, jeda=1.0)
        
        log_step("# 35. Klik Beralih ke sandi/pin")
        
        # 35. Klik Beralih ke sandi/pin
        tap(531, 2302, jeda=0.9)
        
        log_step("# 36. Masukkan PIN dinamis lagi")
        
        # 36. Masukkan PIN dinamis lagi
        tap_dynamic_pin(PIN, KEYPAD, final_jeda=4.0)
        
        log_step("# 37. Klik Oke (Hasil penarikan dikirim)")
        
        # 37. Klik Oke (Hasil penarikan dikirim)
        tap(533, 2310, jeda=0.5)
        
        # ==========================================
        # KEMBALI KE MULTI APP
        # ==========================================
        print("Proses berhasil, langsung membuka Multi App (Pemanggilan Paket)...")
        log_step("# 38. Buka kembali Multi App Ultra (via Package Name)")
        adb_command("shell monkey -p com.waxmoon.ma.gp -c android.intent.category.LAUNCHER 1")
        stoppable_sleep(1.0)
        
        log_step("# 40. Klik Titik Tiga (Menu Multi App)")
        
        # 40. Klik Titik Tiga (Menu Multi App)
        tap(1032, 145, jeda=0.6)
        
        log_step("# 41. Klik Kill All Apps")
        
        # 41. Klik Kill All Apps
        tap(773, 273, jeda=0.9)
        
        log_step("# 42. Klik Confirm (Kill All Apps)")
        
        # 42. Klik Confirm (Kill All Apps)
        tap(846, 1284, jeda=5.5)
        
    print("\nSemua akun selesai diproses.")

if __name__ == "__main__":
    main()
