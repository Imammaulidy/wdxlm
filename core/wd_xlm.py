import subprocess
import time
import os
import platform
import sys
import json
import atexit

# Root Direktori Proyek
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Tambahkan path folder scrcpy / adb ke environment variables agar dikenali otomatis (hanya untuk PC)
if not IS_TERMUX:
    candidates = [
        os.path.join(PROJECT_ROOT, "core", "QtScrcpy-win-x64-v3.3.3"),
        os.path.join(PROJECT_ROOT, "core", "scrcpy-win64-v3.3.4"),
        r"C:\Users\KAGE\Desktop\scrcpy-win64-v3.3.4",
        os.path.join(os.path.expanduser("~"), "Desktop", "scrcpy-win64-v3.3.4"),
    ]
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(desktop_dir):
        for item in os.listdir(desktop_dir):
            if "scrcpy" in item.lower():
                candidates.append(os.path.join(desktop_dir, item))

    for p in candidates:
        if os.path.exists(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

if platform.system() == "Windows":
    import msvcrt

current_step_info = "Menyiapkan bot..."

def log_step(text):
    global current_step_info
    current_step_info = text
    print(f"\n---> {text}")

MANUAL_MODE = "--manual" in sys.argv

def stoppable_sleep(jeda):
    """Tunggu selama 'jeda' detik. Jika di Windows dan ENTER ditekan, PAUSE script."""
    end_time = time.time() + jeda
    has_manual_paused = False
    while time.time() < end_time:
        paused = False
        if MANUAL_MODE and not has_manual_paused:
            paused = True
            has_manual_paused = True
            
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
            sisa_waktu = max(0, end_time - time.time())
            if MANUAL_MODE:
                print(f"\n[STEP-BY-STEP] Menunggu konfirmasi...")
                print(f"[*] SELESAI: {current_step_info}")
                print(" --> Tekan ENTER untuk MELANJUTKAN eksekusi berikutnya")
            else:
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
                            print("\n[>] MELANJUTKAN PROSES DALAM 3 DETIK...")
                            print("[!] SEGERA TUTUP KEYBOARD ATAU KEMBALI KE APLIKASI!")
                            time.sleep(1)
                            print("3...")
                            time.sleep(1)
                            print("2...")
                            time.sleep(1)
                            print("1...")
                            time.sleep(1)
                            print("GO!\n")
                            end_time = time.time() + sisa_waktu
                            break
                        elif resume_key in ('q', 'x'):
                            print("\n[X] EKSEKUSI DIHENTIKAN PAKSA OLEH PENGGUNA.")
                            sys.exit(0)
                        else:
                            print("\n[>] MELANJUTKAN PROSES DALAM 3 DETIK...")
                            print("[!] SEGERA TUTUP KEYBOARD ATAU KEMBALI KE APLIKASI!")
                            time.sleep(1)
                            print("3...")
                            time.sleep(1)
                            print("2...")
                            time.sleep(1)
                            print("1...")
                            time.sleep(1)
                            print("GO!\n")
                            end_time = time.time() + sisa_waktu
                            break
            
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
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Gagal memuat {CONFIG_FILE}: {e}")
        sys.exit(1)

is_screen_modified = False

def setup_screen_resolution():
    """Menyetel resolusi dan density ke format standar bot (1080x2400 @ 352 DPI)."""
    global is_screen_modified
    print("[*] Menyesuaikan resolusi layar otomatis ke standar bot (1080x2400 @ 352 DPI)...")
    adb_command("shell wm size 1080x2400")
    adb_command("shell wm density 352")
    is_screen_modified = True

def restore_screen_resolution():
    """Mengembalikan resolusi dan density ke setelan bawaan HP masing-masing."""
    global is_screen_modified
    if is_screen_modified:
        print("\n[*] Mengembalikan resolusi layar HP ke setelan bawaan pabrik...")
        adb_command("shell wm size reset")
        adb_command("shell wm density reset")
        is_screen_modified = False
        print("[V] Layar HP berhasil dikembalikan ke normal!")

atexit.register(restore_screen_resolution)

DISABLED_STEPS = []

def is_step_enabled(step_num):
    """Cek apakah step tertentu aktif (tidak di-disable)."""
    return step_num not in DISABLED_STEPS

def run_bot(config):
    global DISABLED_STEPS
    # Konfigurasi Looping
    TOTAL_AKUN = config.get("total_akun", 5)
    ALAMAT_WD = config.get("alamat_wd", "")
    PIN = config.get("pin", "080808")
    KEYPAD = config.get("keypad_coords", {})
    DISABLED_STEPS = config.get("disabled_steps", [])

    # Nomor Urut Awal untuk Penamaan di Google Authenticator
    START_INDEX = config.get("start_index", 51)

    print(f"\n[?] Bot akan memproses {TOTAL_AKUN} akun sekaligus.")
    inp_start = input(f"[?] Mulai dari clone nomor berapa? (Tekan Enter untuk {START_INDEX}): ").strip()
    if inp_start.isdigit():
        START_INDEX = int(inp_start)

    # Simpan index berikutnya ke config.json agar diingat pada eksekusi selanjutnya
    config["start_index"] = START_INDEX + TOTAL_AKUN
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

    if DISABLED_STEPS:
        print(f"[!] Step yang di-SKIP: {DISABLED_STEPS}")

    print(f"\n[*] PROSES DIMULAI DARI CLONE KE-{START_INDEX} ...\n")

    for i in range(TOTAL_AKUN):
        current_account_num = START_INDEX + i
        print(f"\n========== MEMPROSES AKUN KE-{current_account_num} ==========")

        # Step 0
        if is_step_enabled(0):
            log_step("# 0. Scroll layar Multi App agar clone berikutnya naik ke atas")
            print("Menggeser layar Multi App Ultra...")
            swipe(546, 820, 546, 500, duration=1200, jeda=1.0)
        else:
            print("[SKIP] Step 0: Scroll Multi App")

        # Step 1
        if is_step_enabled(1):
            log_step("# 1. KLIK BITGET (Buka clone aplikasi dari Multi App)")
            tap(164, 423, jeda=6.6)
        else:
            print("[SKIP] Step 1: Klik Bitget")

        # Step 2
        if is_step_enabled(2):
            log_step("# 2. Klik Dompet (Klik 2 kali)")
            tap(908, 2258, jeda=1.8)
            tap(908, 2258, jeda=1.6)
        else:
            print("[SKIP] Step 2: Klik Dompet")

        # Step 2.1
        if is_step_enabled("2.1"):
            log_step("# 2.1 Swipe bawah (tutup popup default jika muncul)")
            print("Swipe bawah (menutup popup jika ada)...")
            swipe(560, 1630, 580, 2377, duration=300, jeda=2.3)
        else:
            print("[SKIP] Step 2.1: Swipe tutup popup")

        # Step 3
        if is_step_enabled(3):
            log_step("# 3. Klik Hadiah")
            tap(212, 816, jeda=3.2)
        else:
            print("[SKIP] Step 3: Klik Hadiah")

        # Step 4
        if is_step_enabled(4):
            log_step("# 4. Klik XLM")
            tap(536, 1316, jeda=2.4)
        else:
            print("[SKIP] Step 4: Klik XLM")

        # Step 5
        if is_step_enabled(5):
            log_step("# 5. Klik Penarikan")
            tap(533, 2302, jeda=1.9)
        else:
            print("[SKIP] Step 5: Klik Penarikan")

        # Step 6
        if is_step_enabled(6):
            log_step("# 6. Klik Alamat Tujuan & Input Alamat")
            tap(525, 631, jeda=0.8)
            input_text(ALAMAT_WD, jeda=1.7)
        else:
            print("[SKIP] Step 6: Input Alamat")

        # Step 7
        if is_step_enabled(7):
            log_step("# 7. Klik Semua (Max Amount)")
            tap(969, 888, jeda=1.6)
        else:
            print("[SKIP] Step 7: Klik Semua")

        # Step 8
        if is_step_enabled(8):
            log_step("# 8. Klik area kosong untuk menghilangkan keyboard")
            tap(518, 1452, jeda=1.3)
        else:
            print("[SKIP] Step 8: Tutup keyboard")

        # Step 9
        if is_step_enabled(9):
            log_step("# 9. Klik Konfirmasi")
            tap(541, 2307, jeda=1.2)
        else:
            print("[SKIP] Step 9: Klik Konfirmasi")

        # Step 10
        if is_step_enabled(10):
            log_step("# 10. Klik Konfirmasi Lagi (Modal Pengingat)")
            tap(800, 2156, jeda=1.2)
        else:
            print("[SKIP] Step 10: Konfirmasi Modal Pengingat")

        # Step 11
        if is_step_enabled(11):
            log_step("# 11. Klik Selanjutnya (Halaman Ikat Google Auth)")
            tap(530, 2307, jeda=2.4)
        else:
            print("[SKIP] Step 11: Klik Selanjutnya")

        # Step 12
        if is_step_enabled(12):
            log_step("# 12. Klik Copy Kode")
            tap(982, 1106, jeda=1.0)
        else:
            print("[SKIP] Step 12: Copy Kode")

        # Step 13
        if is_step_enabled(13):
            log_step("# 13. Klik Selanjutnya")
            tap(531, 1676, jeda=1.2)
        else:
            print("[SKIP] Step 13: Klik Selanjutnya")

        # Step 14
        if is_step_enabled(14):
            log_step("# 14. Buka Google Authenticator")
            print("Membuka Google Authenticator...")
            adb_command("shell monkey -p com.google.android.apps.authenticator2 -c android.intent.category.LAUNCHER 1")
            stoppable_sleep(2.5)
        else:
            print("[SKIP] Step 14: Buka Google Auth")

        # Step 15
        if is_step_enabled(15):
            log_step("# 15. Klik Tambah Kode (+) di Google Auth")
            tap(985, 2287, jeda=1.4)
        else:
            print("[SKIP] Step 15: Tambah Kode Google Auth")

        # Step 16
        if is_step_enabled(16):
            log_step("# 16. Klik Masukkan Kunci Penyiapan")
            tap(963, 2066, jeda=1.2)
        else:
            print("[SKIP] Step 16: Masukkan Kunci Penyiapan")

        # Step 17
        if is_step_enabled(17):
            log_step("# 17. Klik Nama Kode dan Masukkan Nomor Urut Otomatis")
            tap(166, 320, jeda=1.0)
            input_text(str(current_account_num), jeda=0.8)
        else:
            print("[SKIP] Step 17: Input Nama Kode")

        # Step 18
        if is_step_enabled(18):
            log_step("# 18. Klik Kunci Anda dan Paste Kode")
            tap(338, 508, jeda=1.0)
            paste_clipboard(jeda=1.1)
        else:
            print("[SKIP] Step 18: Paste Kode")

        # Step 19
        if is_step_enabled(19):
            log_step("# 19. Pencet Back untuk menutup keyboard")
            press_back(jeda=0.9)
        else:
            print("[SKIP] Step 19: Tutup Keyboard (Back)")

        # Step 20
        if is_step_enabled(20):
            log_step("# 20. Klik Tambahkan")
            tap(536, 2279, jeda=2.1)
        else:
            print("[SKIP] Step 20: Klik Tambahkan")

        # Step 21
        if is_step_enabled(21):
            log_step("# 21. Klik Tutup (layar blank/secure)")
            tap(983, 2256, jeda=1.0)
        else:
            print("[SKIP] Step 21: Klik Tutup")

        # Step 22
        if is_step_enabled(22):
            log_step("# 22. Scroll ke bawah mentok (Diulang 2 kali)")
            swipe(525, 2140, 556, 220, duration=1000, jeda=0.6)
            swipe(525, 2140, 556, 220, duration=1000, jeda=0.4)
        else:
            print("[SKIP] Step 22: Scroll bawah")

        # Step 23
        if is_step_enabled(23):
            log_step("# 23. Klik Code OTP di paling bawah untuk meng-copy-nya")
            tap(535, 2285, jeda=1.0)
        else:
            print("[SKIP] Step 23: Copy OTP")

        # Step 24
        if is_step_enabled(24):
            log_step("# 24. Buka Recent Apps")
            open_recent_apps(jeda=0.9)
        else:
            print("[SKIP] Step 24: Buka Recent Apps")

        # Step 25
        if is_step_enabled(25):
            log_step("# 25. Klik Bitget Wallet di sebelah kanan")
            tap(851, 1329, jeda=1.1)
        else:
            print("[SKIP] Step 25: Klik Bitget Wallet")

        # Step 26
        if is_step_enabled(26):
            log_step("# 26. Klik tombol Tempel (di Bitget Wallet)")
            tap(920, 426, jeda=0.6)
        else:
            print("[SKIP] Step 26: Tempel di Bitget Wallet")

        # Step 27
        if is_step_enabled(27):
            log_step("# 27. Klik Ikat")
            tap(525, 2310, jeda=1.2)
        else:
            print("[SKIP] Step 27: Klik Ikat")

        # Step 28
        if is_step_enabled(28):
            log_step("# 28. Klik area kosong (agar ganti metode FP ke PIN)")
            tap(528, 1270, jeda=1.1)
        else:
            print("[SKIP] Step 28: Ganti metode FP ke PIN")

        # Step 29
        if is_step_enabled(29):
            log_step("# 29. Klik Beralih ke sandi/pin")
            tap(546, 2302, jeda=0.9)
        else:
            print("[SKIP] Step 29: Beralih ke PIN")

        # Step 30
        if is_step_enabled(30):
            log_step("# 30. Masukkan PIN dinamis via sentuhan layar")
            tap_dynamic_pin(PIN, KEYPAD, final_jeda=2.5)
        else:
            print("[SKIP] Step 30: Input PIN")

        # Step 31
        if is_step_enabled(31):
            log_step("# 31. Klik Konfirmasi (setelah kembali ke halaman WD)")
            tap(536, 2302, jeda=0.9)
        else:
            print("[SKIP] Step 31: Konfirmasi WD")

        # Step 32
        if is_step_enabled(32):
            log_step("# 32. Klik Tempel (di modal Otentikasi Google)")
            tap(946, 2027, jeda=0.4)
        else:
            print("[SKIP] Step 32: Tempel OTP Google")

        # Step 33
        if is_step_enabled(33):
            log_step("# 33. Klik Otentikasi")
            tap(797, 2233, jeda=1.2)
        else:
            print("[SKIP] Step 33: Klik Otentikasi")

        # Step 34
        if is_step_enabled(34):
            log_step("# 34. Klik area kosong (Ganti metode)")
            tap(495, 1093, jeda=1.0)
        else:
            print("[SKIP] Step 34: Ganti metode")

        # Step 35
        if is_step_enabled(35):
            log_step("# 35. Klik Beralih ke sandi/pin")
            tap(531, 2302, jeda=0.9)
        else:
            print("[SKIP] Step 35: Beralih ke PIN (ke-2)")

        # Step 36
        if is_step_enabled(36):
            log_step("# 36. Masukkan PIN dinamis lagi")
            tap_dynamic_pin(PIN, KEYPAD, final_jeda=4.0)
        else:
            print("[SKIP] Step 36: Input PIN ke-2")

        # Step 37
        if is_step_enabled(37):
            log_step("# 37. Klik Oke (Hasil penarikan dikirim)")
            tap(533, 2310, jeda=0.5)
        else:
            print("[SKIP] Step 37: Klik Oke")

        # Step 38
        if is_step_enabled(38):
            print("Proses berhasil, langsung membuka Multi App (Pemanggilan Paket)...")
            log_step("# 38. Buka kembali Multi App Ultra (via Package Name)")
            adb_command("shell monkey -p com.waxmoon.ma.gp -c android.intent.category.LAUNCHER 1")
            stoppable_sleep(1.0)
        else:
            print("[SKIP] Step 38: Buka Multi App")

        # Step 40
        if is_step_enabled(40):
            log_step("# 40. Klik Titik Tiga (Menu Multi App)")
            tap(1032, 145, jeda=0.6)
        else:
            print("[SKIP] Step 40: Menu Multi App")

        # Step 41
        if is_step_enabled(41):
            log_step("# 41. Klik Kill All Apps")
            tap(773, 273, jeda=0.9)
        else:
            print("[SKIP] Step 41: Kill All Apps")

        # Step 42
        if is_step_enabled(42):
            log_step("# 42. Klik Confirm (Kill All Apps)")
            tap(846, 1284, jeda=5.5)
        else:
            print("[SKIP] Step 42: Confirm Kill All")

    print("\nSemua akun selesai diproses.")

def main():
    config = load_config()
    print("Starting Bitget Wallet XLM Withdrawal Script...")
    
    log_step("# 1. Pastikan device terkoneksi")
    
    # 1. Pastikan device terkoneksi
    devices = adb_command("devices")
    if "device" not in devices:
        print("Device tidak ditemukan! Pastikan sudah terkoneksi via USB / WiFi ADB.")
        sys.exit()
    print(f"Connected devices:\n{devices}")
    
    # Ambil perangkat pertama yang valid untuk menghindari error 'more than one device'
    valid_devices = [line.split()[0] for line in devices.splitlines() if 'device' in line and not line.startswith('List')]
    
    if len(valid_devices) > 1:
        non_mdns = [d for d in valid_devices if not d.startswith('adb-')]
        if non_mdns:
            valid_devices = non_mdns
    if valid_devices:
        os.environ['ANDROID_SERIAL'] = valid_devices[0]
        print(f"[*] Menargetkan perintah ADB ke perangkat: {valid_devices[0]}\n")
    
    try:
        setup_screen_resolution()
        run_bot(config)
    finally:
        restore_screen_resolution()

if __name__ == "__main__":
    main()
