import os
import json
import sys
import time
import subprocess
import shutil

# Root Direktori Proyek
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
CONFIG_EXAMPLE = os.path.join(CORE_DIR, 'config.example.json')

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Tambahkan path folder scrcpy / adb ke environment variables agar dikenali otomatis (PC)
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

def launch_mirror_screen():
    qtscrcpy_dir = os.path.join(PROJECT_ROOT, "core", "QtScrcpy-win-x64-v3.3.3")
    qtscrcpy_exe = os.path.join(qtscrcpy_dir, "QtScrcpy.exe")
    if os.path.exists(qtscrcpy_exe):
        print("[*] Menjalankan QtScrcpy...")
        subprocess.Popen([qtscrcpy_exe], cwd=qtscrcpy_dir)
    elif shutil.which("QtScrcpy.exe"):
        print("[*] Menjalankan QtScrcpy...")
        os.system('start /B QtScrcpy.exe' if os.name == 'nt' else 'QtScrcpy &')
    elif shutil.which("scrcpy.exe") or shutil.which("scrcpy"):
        print("[*] Menjalankan scrcpy...")
        os.system('start /B scrcpy.exe' if os.name == 'nt' else 'scrcpy &')
    else:
        print("[!] Program SCRCPY (QtScrcpy.exe / scrcpy.exe) tidak ditemukan di folder core!")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(CONFIG_EXAMPLE):
            shutil.copy(CONFIG_EXAMPLE, CONFIG_FILE)
            print("[*] config.json baru berhasil dibuat dari template otomatis!")
            time.sleep(1)
        else:
            print("Error: config.json dan config.example.json tidak ditemukan!")
            sys.exit(1)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

ALL_STEPS = [
    (0,    "Scroll layar Multi App agar clone naik ke atas"),
    (1,    "KLIK BITGET (Buka clone dari Multi App)"),
    (2,    "Klik Dompet (2 kali)"),
    ("2.1","Swipe bawah (tutup popup default)"),
    (3,    "Klik Hadiah"),
    (4,    "Klik XLM"),
    (5,    "Klik Penarikan"),
    (6,    "Klik Alamat Tujuan & Input Alamat"),
    (7,    "Klik Semua (Max Amount)"),
    (8,    "Klik area kosong (hilangkan keyboard)"),
    (9,    "Klik Konfirmasi"),
    (10,   "Klik Konfirmasi Lagi (Modal Pengingat)"),
    (11,   "Klik Selanjutnya (Ikat Google Auth)"),
    (12,   "Klik Copy Kode"),
    (13,   "Klik Selanjutnya"),
    (14,   "Buka Google Authenticator"),
    (15,   "Klik Tambah Kode (+) di Google Auth"),
    (16,   "Klik Masukkan Kunci Penyiapan"),
    (17,   "Input Nama Kode (Nomor Urut)"),
    (18,   "Klik Kunci Anda & Paste Kode"),
    (19,   "Pencet Back (tutup keyboard)"),
    (20,   "Klik Tambahkan"),
    (21,   "Klik Tutup (layar blank/secure)"),
    (22,   "Scroll ke bawah mentok (2x)"),
    (23,   "Klik Code OTP (copy)"),
    (24,   "Buka Recent Apps"),
    (25,   "Klik Bitget Wallet (kanan)"),
    (26,   "Klik Tempel di Bitget Wallet"),
    (27,   "Klik Ikat"),
    (28,   "Klik area kosong (ganti FP ke PIN)"),
    (29,   "Klik Beralih ke sandi/pin"),
    (30,   "Masukkan PIN (via koordinat sentuh)"),
    (31,   "Klik Konfirmasi (halaman WD)"),
    (32,   "Klik Tempel (modal Otentikasi Google)"),
    (33,   "Klik Otentikasi"),
    (34,   "Klik area kosong (Ganti metode ke-2)"),
    (35,   "Klik Beralih ke sandi/pin (ke-2)"),
    (36,   "Masukkan PIN ke-2"),
    (37,   "Klik Oke (WD dikirim)"),
    (38,   "Buka Multi App Ultra (via package)"),
    (40,   "Klik Titik Tiga (Menu Multi App)"),
    (41,   "Klik Kill All Apps"),
    (42,   "Klik Confirm (Kill All Apps)"),
]

def print_menu():
    clear_screen()
    print("=========================================================")
    print("              BOT AUTO WD XLM BITGET                     ")
    print("=========================================================")

    config = load_config()
    addr = config.get('alamat_wd', '')
    addr_disp = f"{addr[:15]}...{addr[-5:]}" if len(addr) > 20 else addr
    disabled_count = len(config.get('disabled_steps', []))
    step_status = f"[{len(ALL_STEPS) - disabled_count}/{len(ALL_STEPS)} Step Aktif]"
    print(f"[*] Address Saat Ini : {addr_disp}")
    print(f"[*] PIN Saat Ini     : {config.get('pin')}")
    print(f"[*] Total Akun WD    : {config.get('total_akun')}")
    print(f"[*] Step Bot         : {step_status}")
    print("=========================================================")
    print("1. MULAI WD (OTOMATIS FULL)")
    print("2. MULAI WD MANUAL (VIA ENTER / STEP-BY-STEP)")
    print("3. GANTI ADDRESS PENERIMA DAN PIN")
    print("4. ON/OFF STEP KOORDINAT BOT")
    print("5. PENGATURAN RESOLUSI & DPI LAYAR HP")
    print("6. RESTART MENU UTAMA")
    if IS_TERMUX:
        print("7. KONEK ADB LOKAL (WIRELESS DEBUGGING)")
        print("8. INSTALL/UPDATE DEPENDENCIES")
        print("9. BUKA PENGATURAN DEVELOPER (Shortcut)")
    else:
        print("7. KONEK ADB & SCRCPY (KHUSUS PC)")
    print("0. EXIT")
    print("=========================================================")

def ganti_pengaturan():
    config = load_config()
    print("\n--- GANTI PENGATURAN ---")
    print("Kosongkan lalu tekan Enter jika tidak ingin mengubah data.")
    
    # Address
    baru_address = input(f"Address ({config.get('alamat_wd')}): ").strip()
    if baru_address != "":
        config['alamat_wd'] = baru_address
        
    # PIN
    baru_pin = input(f"PIN Baru ({config.get('pin')}): ").strip()
    if baru_pin != "":
        if not baru_pin.isdigit():
            print("ERROR: PIN harus berupa angka!")
        else:
            config['pin'] = baru_pin
            
    # Total Akun
    baru_total = input(f"Total Akun ({config.get('total_akun')}): ").strip()
    if baru_total != "":
        if baru_total.isdigit():
            config['total_akun'] = int(baru_total)
            
    save_config(config)
    print("\n[!] Pengaturan berhasil disimpan!")
    input("Tekan Enter untuk kembali ke menu...")

def menu_toggle_steps():
    while True:
        config = load_config()
        disabled = config.get("disabled_steps", [])
        clear_screen()
        print("=========================================================")
        print("        PENGATURAN ON/OFF STEP KOORDINAT BOT             ")
        print("=========================================================")
        print(f"  {'NO':>4}  {'STEP':<5}  {'STATUS':<6}  DESKRIPSI")
        print("---------------------------------------------------------")
        for idx, (step_id, desc) in enumerate(ALL_STEPS, start=1):
            status = "[ ON ]" if step_id not in disabled else "[OFF ]"
            print(f"  {idx:>4}. Step {str(step_id):<4} {status}  {desc}")
        print("---------------------------------------------------------")
        print("  A  = AKTIFKAN SEMUA STEP")
        print("  D  = DISABLE SEMUA STEP")
        print("  0  = Kembali ke Menu Utama")
        print("=========================================================")
        pil = input("Masukkan nomor step untuk toggle (atau A/D/0): ").strip().upper()

        if pil == '0':
            break
        elif pil == 'A':
            config["disabled_steps"] = []
            save_config(config)
            print("[V] Semua step DIAKTIFKAN!")
            time.sleep(1)
        elif pil == 'D':
            config["disabled_steps"] = [s for s, _ in ALL_STEPS]
            save_config(config)
            print("[!] Semua step DINONAKTIFKAN!")
            time.sleep(1)
        elif pil.isdigit():
            idx_pil = int(pil) - 1
            if 0 <= idx_pil < len(ALL_STEPS):
                step_id, desc = ALL_STEPS[idx_pil]
                if step_id in disabled:
                    disabled.remove(step_id)
                    print(f"[V] Step {step_id} [{desc}] -> ON")
                else:
                    disabled.append(step_id)
                    print(f"[!] Step {step_id} [{desc}] -> OFF")
                config["disabled_steps"] = disabled
                save_config(config)
                time.sleep(0.6)
            else:
                print("Nomor tidak valid!")
                time.sleep(1)
        else:
            print("Pilihan tidak dikenali!")
            time.sleep(1)

def menu_resolusi_layar():
    while True:
        clear_screen()
        print("=========================================================")
        print("           PENGATURAN RESOLUSI & DPI LAYAR               ")
        print("=========================================================")
        print("1. Cek Resolusi & DPI Saat Ini")
        print("2. Samakan ke Format Bot POCO F4 (1080x2400 @ 352 DPI)")
        print("3. Restore ke Bawaan Asli HP (Reset Pabrik)")
        print("0. Kembali ke Menu Utama")
        print("=========================================================")
        pil = input("Pilih menu (0-3): ").strip()

        if pil == '1':
            print("\n[*] Membaca status layar...")
            os.system('adb shell "wm size && wm density"')
            input("\nTekan Enter untuk melanjutkan...")
        elif pil == '2':
            print("\n[*] Mengatur layar ke standar bot POCO F4 (1080x2400 @ 352 DPI)...")
            os.system('adb shell "wm size 1080x2400 && wm density 352"')
            print("[V] Berhasil disetel!")
            input("\nTekan Enter untuk melanjutkan...")
        elif pil == '3':
            print("\n[*] Mengembalikan layar ke setelan bawaan asli HP...")
            os.system('adb shell "wm size reset && wm density reset"')
            print("[V] Layar berhasil di-reset!")
            input("\nTekan Enter untuk melanjutkan...")
        elif pil == '0':
            break

def konek_adb_scrcpy():
    clear_screen()
    print(">>> KONEKSI ADB & SCRCPY (PC) <<<\n")
    print("1. ADB USB/WiFi + Buka Layar (SCRCPY)")
    print("2. Hanya Buka Layar (SCRCPY)")
    print("3. Hanya Konek ADB via IP (WiFi)")
    print("4. Auto-Setup Wireless (Colok USB sebentar) - DIREKOMENDASIKAN")
    print("5. Pairing Perangkat Baru (Khusus Android 11+)")
    print("0. Batal")
    
    pil = input("\nPilih mode (0-5): ").strip()
    
    if pil == '1':
        ip = input("Masukkan IP:PORT HP (Cek Developer Options, misal 192.168.x.x:41234).\nKosongkan jika pakai kabel USB atau ingin default 192.168.2.176: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
        launch_mirror_screen()
            
    elif pil == '2':
        launch_mirror_screen()
            
    elif pil == '3':
        ip = input("Masukkan IP:PORT HP [Tekan Enter untuk default 192.168.2.176]: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
            
    elif pil == '4':
        print("\n=== AUTO-SETUP WIRELESS ===")
        print("Syarat: Sambungkan HP ke PC pakai Kabel USB sebentar saja.")
        input("Tekan Enter jika KABEL USB SUDAH TERSAMBUNG...")
        
        print("\n[*] Membersihkan koneksi lama dan menyetel port USB ke 5555...")
        os.system('adb disconnect')
        os.system('adb -d tcpip 5555')
        
        print("\n[!] SUKSES! Sekarang CABUT KABEL USB Anda.")
        ip = input("Masukkan IP HP Anda [Tekan Enter untuk default: 192.168.2.176]: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi Nirkabel ke {ip}:5555...")
            os.system(f'adb connect {ip}:5555')
            
    elif pil == '5':
        print("\n=== PAIRING ANDROID 11+ ===")
        print("1. Buka Opsi Developer -> Proses Debug Nirkabel.")
        print("2. Klik 'Pasangkan perangkat dengan kode penyandingan'.")
        print("3. Lihat Alamat IP & Port, dan 6 digit Kode.")
        ip_port = input("Masukkan IP:PORT Pairing (misal 192.168.x.x:35612): ").strip()
        code = input("Masukkan 6 Digit Kode Pairing: ").strip()
        if ip_port and code:
            os.system(f'adb pair {ip_port} {code}')
            
    if pil in ['1', '2', '3', '4', '5']:
        input("\nProses selesai. Tekan Enter untuk kembali ke menu...")

def main():
    wd_script = os.path.join(os.path.dirname(__file__), 'wd_xlm.py')
    konek_script = os.path.join(PROJECT_ROOT, 'termux', 'konek_adb.py')
    setup_script = os.path.join(PROJECT_ROOT, 'termux', 'setup.sh')

    while True:
        print_menu()
        if IS_TERMUX:
            pilihan = input("Pilih menu (0-9): ").strip()
        else:
            pilihan = input("Pilih menu (0-7): ").strip()

        if pilihan == '1':
            clear_screen()
            print(">>> MENJALANKAN WD OTOMATIS <<<\n")
            subprocess.run([sys.executable, wd_script], cwd=PROJECT_ROOT)
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")

        elif pilihan == '2':
            clear_screen()
            print(">>> MENJALANKAN WD MANUAL (STEP-BY-STEP) <<<\n")
            subprocess.run([sys.executable, wd_script, '--manual'], cwd=PROJECT_ROOT)
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")

        elif pilihan == '3':
            ganti_pengaturan()

        elif pilihan == '4':
            menu_toggle_steps()

        elif pilihan == '5':
            menu_resolusi_layar()

        elif pilihan == '6':
            clear_screen()
            print("[*] Merestart ulang sistem Menu Utama...")
            time.sleep(1)
            os.execv(sys.executable, [sys.executable, __file__] + sys.argv[1:])

        elif pilihan == '7':
            if IS_TERMUX:
                clear_screen()
                print("=========================================================")
                print("SYARAT: Nyalakan 'Proses Debug Nirkabel' (Wireless Debugging)")
                print("di Pengaturan Developer HP Anda sebelum melanjutkan.")
                print("=========================================================")
                subprocess.run([sys.executable, konek_script], cwd=PROJECT_ROOT)
                print("\n")
                input("Tekan Enter untuk kembali ke menu...")
            else:
                konek_adb_scrcpy()

        elif pilihan == '8' and IS_TERMUX:
            clear_screen()
            subprocess.run(['bash', setup_script], cwd=PROJECT_ROOT)
            print("\n")
            input("Tekan Enter untuk kembali ke menu...")

        elif pilihan == '9' and IS_TERMUX:
            clear_screen()
            print("[*] Membuka Pengaturan Developer di HP Anda...")
            os.system('am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS')
            print("\n")
            input("Tekan Enter untuk kembali ke menu...")

        elif pilihan == '0':
            clear_screen()
            print("Keluar dari program. Terima kasih!")
            sys.exit(0)

        else:
            print("Pilihan tidak valid!")
            time.sleep(1)

if __name__ == "__main__":
    main()
