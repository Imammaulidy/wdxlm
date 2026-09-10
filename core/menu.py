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

def get_scrcpy_exe():
    """Mencari path executable scrcpy.exe di folder core."""
    p = os.path.join(PROJECT_ROOT, "core", "scrcpy-win64-v3.3.4", "scrcpy.exe")
    if os.path.exists(p):
        return p
    which = shutil.which("scrcpy.exe") or shutil.which("scrcpy")
    if which:
        return which
    return None

def launch_mirror_screen(extra_args=""):
    scrcpy_exe = get_scrcpy_exe()
    if scrcpy_exe:
        print("[*] Menjalankan scrcpy...")
        cmd = f'start "" "{scrcpy_exe}" {extra_args}'.strip() if os.name == 'nt' else f'"{scrcpy_exe}" {extra_args} &'
        os.system(cmd)
    else:
        print("[!] Program scrcpy.exe tidak ditemukan di folder core/scrcpy-win64-v3.3.4!")

def detect_device_wifi_ip(target_serial=None):
    """
    Mendeteksi IP Wi-Fi murni dari interface wlan0 atau wlan1.
    TIDAK AKAN membaca interface seluler/data (rmnet) atau loopback.
    """
    prefix = f"adb -s {target_serial} " if target_serial else "adb -d "
    for iface in ["wlan0", "wlan1"]:
        try:
            out = subprocess.run(f"{prefix}shell ip -f inet addr show {iface}", shell=True, capture_output=True, text=True, timeout=3).stdout
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                ip = m.group(1)
                if not ip.startswith("127."):
                    return ip
        except Exception:
            pass
    return None

def is_port_reachable(ip, port=5555, timeout=1.5):
    """Cek cepat apakah port terbuka via TCP socket (mencegah adb hang)."""
    import socket
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def get_usb_device():
    """Mendeteksi ID perangkat USB yang terhubung."""
    try:
        r = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=3)
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and ":" not in parts[0]:
                return parts[0]
    except Exception:
        pass
    return None

def get_or_detect_wifi_ip(target_serial=None):
    """
    Mendeteksi IP dari HP yang terhubung via USB. Jika ditemukan, simpan ke config.json.
    Jika tidak ada HP USB atau Wi-Fi mati, ambil IP terakhir dari config.json.
    """
    config = load_config()
    last_ip = config.get("last_wifi_ip", "")

    detected_ip = detect_device_wifi_ip(target_serial)
    if detected_ip:
        if detected_ip != last_ip:
            config["last_wifi_ip"] = detected_ip
            save_config(config)
        return detected_ip, True
    return last_ip, False


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
    config = load_config()
    last_ip, was_detected = get_or_detect_wifi_ip()

    print("=========================================================")
    print("             KONEKSI ADB & SCRCPY (PC)                   ")
    print("=========================================================")
    if last_ip:
        status_label = "Terdeteksi via USB" if was_detected else "Tersimpan sebelumnya"
        print(f"[*] IP Wi-Fi HP Aktif : {last_ip} ({status_label})")
    else:
        print("[*] IP Wi-Fi HP Aktif : Belum ada (sambungkan USB untuk deteksi otomatis)")
    print("=========================================================")
    print("1. AUTO-SWITCH WIRELESS & BUKA SCRCPY (DIREKOMENDASIKAN)")
    print("   (Colok USB -> otomatis rekam IP -> beralih nirkabel -> buka layar)")
    print("   *Kabel USB bisa dicabut kapan saja, layar tetap aktif!*")
    print("")
    print("2. HANYA BUKA LAYAR (SCRCPY)")
    print("   (Buka mirroring menggunakan koneksi ADB aktif saat ini)")
    print("")
    print("3. KONEK ADB NIRKABEL MANUAL (INPUT IP)")
    print("   (Koneksikan ADB via IP Wi-Fi tanpa menggunakan USB)")
    print("")
    print("4. AUTO-SETUP WIRELESS SAJA (TANPA SCRCPY)")
    print("   (Colok USB -> otomatis rekam IP -> set port 5555)")
    print("")
    print("5. PAIRING ANDROID 11+ (KODE PENYANDINGAN)")
    print("0. Kembali ke Menu Utama")
    print("=========================================================")

    pil = input("Pilih mode (0-5): ").strip()

    if pil == '1':
        print("\n[*] Menyiapkan koneksi...")
        usb_dev = get_usb_device()
        if not usb_dev:
            input("Silakan colokkan kabel USB dari HP ke PC, lalu tekan Enter...")
            usb_dev = get_usb_device()

        if usb_dev:
            print(f"[*] Terdeteksi perangkat USB: {usb_dev}")
            print("[*] Memeriksa status Wi-Fi HP...")
            detected_ip = detect_device_wifi_ip(usb_dev)

            wireless_ready = False
            if detected_ip:
                print(f"[+] Wi-Fi HP aktif. IP terdeteksi: {detected_ip}")
                config["last_wifi_ip"] = detected_ip
                save_config(config)

                print("[*] Menyetel port ADB nirkabel ke 5555...")
                os.system(f"adb -s {usb_dev} tcpip 5555")
                time.sleep(1)

                if is_port_reachable(detected_ip, 5555, timeout=1.5):
                    print(f"[*] Menghubungkan ADB ke {detected_ip}:5555...")
                    os.system(f"adb connect {detected_ip}:5555")
                    wireless_ready = True
                else:
                    print(f"[-] Port {detected_ip}:5555 tidak merespons (beda Wi-Fi / AP Isolation).")
            else:
                print("[*] Wi-Fi HP tidak aktif / tidak terhubung ke jaringan Wi-Fi.")

            if wireless_ready:
                print("\n[V] BERHASIL TERSAMBUNG KE ADB WI-FI!")
                print("[!] KABEL USB SEKARANG SUDAH BISA DICABUT KAPAN SAJA!")
                print("[*] Membuka jendela SCRCPY nirkabel...")
                launch_mirror_screen(f"-s {detected_ip}:5555")
            else:
                print(f"\n[*] Membuka SCRCPY langsung via koneksi USB ({usb_dev})...")
                launch_mirror_screen(f"-s {usb_dev}")
        else:
            if last_ip and is_port_reachable(last_ip, 5555, timeout=1.5):
                print(f"[*] Membuka via Wi-Fi yang diingat: {last_ip}:5555...")
                os.system(f"adb connect {last_ip}:5555")
                launch_mirror_screen(f"-s {last_ip}:5555")
            else:
                print("\n[!] Perangkat tidak ditemukan via USB maupun Wi-Fi.")
                input("Tekan Enter untuk kembali...")

    elif pil == '2':
        launch_mirror_screen()

    elif pil == '3':
        default_prompt = f" [Tekan Enter untuk default {last_ip}]" if last_ip else ""
        ip = input(f"Masukkan IP HP Anda{default_prompt}: ").strip()
        if not ip and last_ip:
            ip = last_ip
        if ip:
            clean_ip = ip if ":" in ip else f"{ip}:5555"
            print(f"[*] Mencoba koneksi ke {clean_ip}...")
            os.system(f'adb connect {clean_ip}')
            config["last_wifi_ip"] = ip.split(":")[0]
            save_config(config)

    elif pil == '4':
        print("\n=== AUTO-SETUP WIRELESS ===")
        print("Syarat: Sambungkan HP ke PC pakai Kabel USB sebentar saja.")
        usb_dev = get_usb_device()
        if not usb_dev:
            input("Tekan Enter jika KABEL USB SUDAH TERSAMBUNG...")
            usb_dev = get_usb_device()

        if not usb_dev:
            print("[!] Perangkat USB tidak terdeteksi.")
            input("Tekan Enter untuk kembali...")
        else:
            detected_ip = detect_device_wifi_ip(usb_dev)
            print(f"\n[*] Menyetel port ADB USB ({usb_dev}) ke 5555...")
            os.system(f"adb -s {usb_dev} tcpip 5555")
            time.sleep(1)

            if detected_ip:
                print(f"[+] IP Wi-Fi HP terdeteksi otomatis: {detected_ip}")
                config["last_wifi_ip"] = detected_ip
                save_config(config)
                if is_port_reachable(detected_ip, 5555, timeout=1.5):
                    print(f"[*] Mengoneksikan ke {detected_ip}:5555...")
                    os.system(f"adb connect {detected_ip}:5555")
                    print("\n[V] SUKSES! Kabel USB sekarang sudah bisa dicabut!")
                else:
                    print(f"[-] Port {detected_ip}:5555 tidak dapat dijangkau dari PC.")
            else:
                print("\n[*] Port 5555 sudah diaktifkan di HP, namun Wi-Fi HP mati / tidak terhubung.")
                print("    Silakan aktifkan Wi-Fi di HP lalu sambungkan menggunakan Opsi 3.")
            input("Tekan Enter untuk kembali...")

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

