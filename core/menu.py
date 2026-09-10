import os
import json
import sys
import time
import subprocess
import shutil
import re

# Root Direktori Proyek
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
CONFIG_EXAMPLE = os.path.join(CORE_DIR, 'config.example.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore,
    get_cached_screen,
    read_current_screen
)

os.environ["BOT_MANAGED_SCREEN"] = "1"


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

def parse_step_header(line):
    """
    Mem-parsing baris judul step, mendeteksi status OFF, ID, dan nama step.
    Contoh: [11. Lanjut Ikat Google Auth] OFF, [24. Buka Recent Apps] 2X, dll.
    """
    m = re.match(r'^\[\s*([^\]]+?)\s*\](?:\s*(.*?))?$', line.strip())
    if not m:
        return None
    inner = m.group(1).strip()
    suffix = (m.group(2) or "").strip()

    is_off = False
    if suffix.upper() == "OFF" or suffix.upper().endswith("OFF"):
        is_off = True
    elif inner.upper().endswith(" OFF"):
        is_off = True
        inner = re.sub(r'\s+OFF$', '', inner, flags=re.IGNORECASE).strip()

    id_m = re.match(r'^([0-9]+(?:\.[0-9]+)?)[.:\s]*(.*)$', inner)
    if id_m:
        raw_id = id_m.group(1)
        step_id = int(raw_id) if raw_id.isdigit() else raw_id
        step_name = id_m.group(2).strip() or inner
    else:
        step_id = inner
        step_name = inner

    if suffix and suffix.upper() != "OFF":
        step_name = f"{step_name} ({suffix})"

    return {
        "id": step_id,
        "name": step_name,
        "full_title": inner,
        "is_off": is_off,
        "suffix": suffix
    }

def get_kordinat_steps():
    """Membaca daftar step langsung dari kordinat.txt secara dinamis."""
    if not os.path.exists(KORDINAT_FILE):
        return []
    steps = []
    with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            header = parse_step_header(stripped)
            if header:
                steps.append(header)
    return steps

def sync_kordinat_and_config():
    """
    Menyinkronkan penanda 'OFF' di kordinat.txt dengan disabled_steps di config.json.
    File kordinat.txt menjadi acuan utama status aktif/nonaktif setiap langkah.
    """
    if not os.path.exists(KORDINAT_FILE) or not os.path.exists(CONFIG_FILE):
        return
    steps = get_kordinat_steps()
    file_disabled = [s['id'] for s in steps if s['is_off']]
    
    config = load_config()
    current_disabled = config.get("disabled_steps", [])
    
    if sorted([str(x) for x in current_disabled]) != sorted([str(x) for x in file_disabled]):
        config["disabled_steps"] = file_disabled
        save_config(config)

def update_kordinat_txt_step(target_step_id, set_off):
    """
    Menulis atau menghapus penanda 'OFF' pada judul step di core/kordinat.txt.
    """
    if not os.path.exists(KORDINAT_FILE):
        return
    with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        m = re.match(r'^(\[\s*([^\]]+?)\s*\])(.*)$', line)
        if not m:
            new_lines.append(line)
            continue
        inner = m.group(2).strip()
        after = m.group(3)
        id_m = re.match(r'^([0-9]+(?:\.[0-9]+)?)[.:\s]*(.*)$', inner)
        raw_id = id_m.group(1) if id_m else inner
        s_id = int(raw_id) if raw_id.isdigit() else raw_id
        if str(s_id) != str(target_step_id):
            new_lines.append(line)
            continue

        clean_after = re.sub(r'\bOFF\b', '', after, flags=re.IGNORECASE).strip()
        clean_inner = re.sub(r'\s+OFF\b', '', inner, flags=re.IGNORECASE).strip()
        new_bracket = f"[{clean_inner}]"
        if set_off:
            new_line = f"{new_bracket} {clean_after} OFF\n" if clean_after else f"{new_bracket} OFF\n"
        else:
            new_line = f"{new_bracket} {clean_after}\n" if clean_after else f"{new_bracket}\n"
        new_lines.append(new_line)

    with open(KORDINAT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def update_all_kordinat_txt_steps(set_off):
    """
    Menyetel penanda 'OFF' untuk seluruh step di core/kordinat.txt (untuk pilihan A atau D).
    """
    if not os.path.exists(KORDINAT_FILE):
        return
    with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        m = re.match(r'^(\[\s*([^\]]+?)\s*\])(.*)$', line)
        if not m:
            new_lines.append(line)
            continue
        inner = m.group(2).strip()
        after = m.group(3)
        clean_after = re.sub(r'\bOFF\b', '', after, flags=re.IGNORECASE).strip()
        clean_inner = re.sub(r'\s+OFF\b', '', inner, flags=re.IGNORECASE).strip()
        new_bracket = f"[{clean_inner}]"
        if set_off:
            new_lines.append(f"{new_bracket} {clean_after} OFF\n" if clean_after else f"{new_bracket} OFF\n")
        else:
            new_lines.append(f"{new_bracket} {clean_after}\n" if clean_after else f"{new_bracket}\n")
    with open(KORDINAT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def print_menu():
    clear_screen()
    print("=========================================================")
    print("              BOT AUTO WD XLM BITGET                     ")
    print("=========================================================")

    sync_kordinat_and_config()
    config = load_config()
    addr = config.get('alamat_wd', '')
    addr_disp = f"{addr[:15]}...{addr[-5:]}" if len(addr) > 20 else addr
    steps = get_kordinat_steps()
    disabled = config.get('disabled_steps', [])
    disabled_str = [str(x) for x in disabled]
    disabled_count = len([s for s in steps if s['is_off'] or s['id'] in disabled or str(s['id']) in disabled_str])
    total_steps = len(steps)
    step_status = f"[{total_steps - disabled_count}/{total_steps} Step Aktif]"
    print(f"[*] Address Saat Ini : {addr_disp}")
    print(f"[*] PIN Saat Ini     : {config.get('pin')}")
    print(f"[*] Total Akun WD    : {config.get('total_akun')}")
    print(f"[*] Step Bot         : {step_status}")
    print("=========================================================")
    print("1. MULAI WD (OTOMATIS FULL)")
    print("2. MULAI WD MANUAL / REKAM DELAY (VIA ENTER)")
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
        sync_kordinat_and_config()
        config = load_config()
        disabled = config.get("disabled_steps", [])
        disabled_str = [str(x) for x in disabled]
        steps = get_kordinat_steps()
        clear_screen()
        print("=========================================================")
        print("        PENGATURAN ON/OFF STEP KOORDINAT BOT             ")
        print("   (Data tersinkronisasi otomatis dengan kordinat.txt)   ")
        print("=========================================================")
        print(f"  {'NO':>4}  {'STEP':<5}  {'STATUS':<6}  DESKRIPSI")
        print("---------------------------------------------------------")
        for idx, step in enumerate(steps, start=1):
            s_id = step['id']
            is_off = step['is_off'] or s_id in disabled or str(s_id) in disabled_str
            status = "[ ON ]" if not is_off else "[OFF ]"
            print(f"  {idx:>4}. Step {str(s_id):<4} {status}  {step['name']}")
        print("---------------------------------------------------------")
        print("  A  = AKTIFKAN SEMUA STEP (Hapus penanda OFF di file)")
        print("  D  = DISABLE SEMUA STEP (Pasang penanda OFF di file)")
        print("  0  = Kembali ke Menu Utama")
        print("=========================================================")
        pil = input("Masukkan nomor step untuk toggle (atau A/D/0): ").strip().upper()

        if pil == '0':
            break
        elif pil == 'A':
            config["disabled_steps"] = []
            save_config(config)
            update_all_kordinat_txt_steps(set_off=False)
            print("[V] Semua step DIAKTIFKAN di menu & kordinat.txt!")
            time.sleep(1)
        elif pil == 'D':
            config["disabled_steps"] = [s['id'] for s in steps]
            save_config(config)
            update_all_kordinat_txt_steps(set_off=True)
            print("[!] Semua step DINONAKTIFKAN di menu & kordinat.txt!")
            time.sleep(1)
        elif pil.isdigit():
            idx_pil = int(pil) - 1
            if 0 <= idx_pil < len(steps):
                step = steps[idx_pil]
                s_id = step['id']
                is_currently_off = step['is_off'] or s_id in disabled or str(s_id) in disabled_str
                new_off_state = not is_currently_off

                if new_off_state:
                    # Menjadi OFF
                    if s_id not in disabled and str(s_id) not in disabled_str:
                        disabled.append(s_id)
                    update_kordinat_txt_step(s_id, set_off=True)
                    print(f"[!] Step {s_id} [{step['name']}] -> OFF (kordinat.txt disinkronkan)")
                else:
                    # Menjadi ON
                    disabled = [x for x in disabled if x != s_id and str(x) != str(s_id)]
                    update_kordinat_txt_step(s_id, set_off=False)
                    print(f"[V] Step {s_id} [{step['name']}] -> ON (kordinat.txt disinkronkan)")

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
        cached_size, cached_density = get_cached_screen()
        cur_info = read_current_screen()
        active_disp = f"{cur_info['active_size']} @ {cur_info['active_density']} DPI" if cur_info['active_size'] else "Tidak terdeteksi (HP belum konek)"
        cached_disp = f"{cached_size} @ {cached_density} DPI" if cached_size and cached_density else "Belum terekam (akan terekam otomatis saat bot mulai)"

        print("=========================================================")
        print("           PENGATURAN RESOLUSI & DPI LAYAR               ")
        print("=========================================================")
        print(f"  Resolusi HP Asli (Terekam) : {cached_disp}")
        print(f"  Resolusi Aktif Saat Ini    : {active_disp}")
        print("=========================================================")
        print("1. Cek Detail Resolusi & DPI (adb shell wm size && density)")
        print("2. Samakan ke Format Bot POCO F4 (1080x2400 @ 352 DPI)")
        print("3. Restore ke Ukuran Asli yang Terekam")
        print("   (Kembalikan layar HP tepat ke ukuran yang sudah terekam)")
        print("0. Kembali ke Menu Utama")
        print("=========================================================")
        pil = input("Pilih menu (0-3): ").strip()

        if pil == '1':
            print("\n[*] Membaca status layar (detail)...")
            os.system('adb shell wm size')
            os.system('adb shell wm density')
            input("\nTekan Enter untuk melanjutkan...")

        elif pil == '2':
            ok, msg = record_and_apply_bot_screen()
            if ok:
                print(f"[V] {msg}")
            input("\nTekan Enter untuk melanjutkan...")

        elif pil == '3':
            ok = restore_recorded_screen()
            if not ok:
                print("[!] Tidak ada rekaman ukuran layar atau HP belum terhubung.")
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

    # Daftarkan pemulihan otomatis layar saat terminal ditutup / exit
    register_auto_restore()

    # Otomatis merekam resolusi asli HP & ubah ke resolusi bot jika HP sudah terhubung
    record_and_apply_bot_screen(silent=True)

    try:
        while True:
            print_menu()
            if IS_TERMUX:
                pilihan = input("Pilih menu (0-9): ").strip()
            else:
                pilihan = input("Pilih menu (0-7): ").strip()

            if pilihan == '1':
                # Pastikan resolusi bot terpasang jika HP baru saja dihubungkan
                record_and_apply_bot_screen(silent=True)
                clear_screen()
                print(">>> MENJALANKAN WD OTOMATIS <<<\n")
                subprocess.run([sys.executable, wd_script], cwd=PROJECT_ROOT)
                print("\n")
                input("Selesai. Tekan Enter untuk kembali ke menu...")

            elif pilihan == '2':
                clear_screen()
                print("=========================================================")
                print("     2. MULAI WD MANUAL / REKAM DELAY (VIA ENTER)        ")
                print("=========================================================")
                print("  A. REKAM DELAY  — Jalankan action + ukur delay HP Anda.")
                print("     Hasil rekaman delay langsung tersimpan ke kordinat.txt")
                print("     dan dipakai saat WD Otomatis (Menu 1) berikutnya.")
                print("")
                print("  B. STEP-BY-STEP — Jalankan bot lengkap, tekan ENTER")
                print("     setelah setiap langkah untuk lanjut ke step berikutnya.")
                print("")
                print("  0. Batal / Kembali")
                print("=========================================================")
                sub = input("Pilih mode (A/B/0): ").strip().upper()
                if sub == 'A':
                    record_and_apply_bot_screen(silent=True)
                    clear_screen()
                    print(">>> REKAM DELAY HP ANDA <<<\n")
                    subprocess.run([sys.executable, wd_script, '--rekam'], cwd=PROJECT_ROOT)
                    print("\n")
                    input("Selesai rekam. Tekan Enter untuk kembali ke menu...")
                elif sub == 'B':
                    record_and_apply_bot_screen(silent=True)
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
                    # Setelah konek, langsung rekam resolusi dan set bot resolusi
                    record_and_apply_bot_screen(silent=True)
                    print("\n")
                    input("Tekan Enter untuk kembali ke menu...")
                else:
                    konek_adb_scrcpy()
                    record_and_apply_bot_screen(silent=True)

            elif pilihan == '8' and IS_TERMUX:
                clear_screen()
                print("[*] Memperbarui dan menginstal dependensi Termux...")
                subprocess.run('pkg update -y && pkg install python nmap android-tools -y', shell=True, cwd=PROJECT_ROOT)
                print("\n")
                input("Selesai. Tekan Enter untuk kembali ke menu...")

            elif pilihan == '9' and IS_TERMUX:
                clear_screen()
                print("[*] Membuka Pengaturan Developer di HP Anda...")
                os.system('am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS')
                print("\n")
                input("Tekan Enter untuk kembali ke menu...")

            elif pilihan == '0':
                clear_screen()
                print("[*] Menutup bot dan memulihkan resolusi layar HP...")
                restore_recorded_screen(silent=False)
                print("Keluar dari program. Terima kasih!")
                sys.exit(0)

            else:
                print("Pilihan tidak valid!")
                time.sleep(1)
    finally:
        restore_recorded_screen(silent=True)

if __name__ == "__main__":
    main()

