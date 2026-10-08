import os
import json
import sys
import time
import subprocess
import shutil
import re

# Root & Core Directory Setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
CONFIG_EXAMPLE = os.path.join(CORE_DIR, 'config.example.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat.txt')
KORDINAT_WD_BARU_FILE = os.path.join(CORE_DIR, 'kordinat_wd_baru.txt')
KORDINAT_WD_OLD_FILE = os.path.join(CORE_DIR, 'kordinat_wd_old.txt')
KORDINAT_CREATE_ACCOUNT_FILE = os.path.join(CORE_DIR, 'kordinat_create_account.txt')
KORDINAT_QRIS_MORPH_FILE = os.path.join(CORE_DIR, 'kordinat_qris_morph.txt')
EMAILS_FILE = os.path.join(CORE_DIR, 'emails.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore,
    get_cached_screen,
    read_current_screen
)
from imap_helper import EmailOTPReader
from wallet_phrase_helper import get_available_wallet_files, load_wallet_phrases
from wd_xlm import prompt_number_with_arrows

os.environ["BOT_MANAGED_SCREEN"] = "1"

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Tambahkan path folder scrcpy / adb ke environment variables (PC)
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
        print("[*] Menjalankan scrcpy (Layar HP fisik dimatikan: -S -w)...")
        flags = extra_args.strip()
        if "-S" not in flags:
            flags = f"{flags} -S -w".strip()
        cmd = f'start "" "{scrcpy_exe}" {flags}'.strip() if os.name == 'nt' else f'"{scrcpy_exe}" {flags} &'
        os.system(cmd)
    else:
        print("[!] Program scrcpy.exe tidak ditemukan di folder core/scrcpy-win64-v3.3.4!")

def detect_device_wifi_ip(target_serial=None):
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
    import socket
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def get_usb_device():
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

def get_key_press(prompt: str = "") -> str:
    """Membaca 1 tombol keyboard secara instan tanpa harus tekan ENTER."""
    if prompt:
        print(prompt, end="", flush=True)

    if os.name == 'nt':
        import msvcrt
        while True:
            try:
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):
                    msvcrt.getch()
                    continue
                if ch == b'\x03':
                    raise KeyboardInterrupt
                ch_str = ch.decode('latin1', errors='ignore')
                if ch_str in ('\r', '\n'):
                    print()
                    return 'enter'
                elif ch_str == ' ':
                    print()
                    return 'space'
                else:
                    print(ch_str)
                    return ch_str
            except Exception:
                pass
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x03':
                raise KeyboardInterrupt
            print(ch)
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def wait_any_key(prompt: str = "\nTekan sembarang tombol untuk kembali..."):
    """Menunggu sembarang tombol ditekan secara instan."""
    print(prompt, end="", flush=True)
    if os.name == 'nt':
        import msvcrt
        try:
            ch = msvcrt.getch()
            if ch == b'\x03':
                raise KeyboardInterrupt
        except Exception:
            pass
        print()
    else:
        try:
            input()
        except KeyboardInterrupt:
            pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists(CONFIG_EXAMPLE):
            shutil.copy(CONFIG_EXAMPLE, CONFIG_FILE)
            print("[*] config.json baru berhasil dibuat dari template otomatis!")
            time.sleep(1)
        else:
            print("Error: config.json dan config.example.json tidak ditemukan!")
            sys.exit(1)
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def parse_step_header(line):
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

def get_kordinat_steps_from_file(filepath):
    if not os.path.exists(filepath):
        return []
    steps = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            header = parse_step_header(stripped)
            if header:
                steps.append(header)
    return steps

def sync_kordinat_and_config():
    if not os.path.exists(CONFIG_FILE):
        return
    config = load_config()
    changed = False

    if os.path.exists(KORDINAT_WD_BARU_FILE):
        steps_wb = get_kordinat_steps_from_file(KORDINAT_WD_BARU_FILE)
        file_disabled_wb = [s['id'] for s in steps_wb if s['is_off']]
        current_disabled_wb = config.get("disabled_steps_wd_baru", config.get("disabled_steps", []))
        if sorted([str(x) for x in current_disabled_wb]) != sorted([str(x) for x in file_disabled_wb]):
            config["disabled_steps_wd_baru"] = file_disabled_wb
            config["disabled_steps"] = file_disabled_wb
            changed = True

    if os.path.exists(KORDINAT_WD_OLD_FILE):
        steps_wo = get_kordinat_steps_from_file(KORDINAT_WD_OLD_FILE)
        file_disabled_wo = [s['id'] for s in steps_wo if s['is_off']]
        current_disabled_wo = config.get("disabled_steps_wd_old", [])
        if sorted([str(x) for x in current_disabled_wo]) != sorted([str(x) for x in file_disabled_wo]):
            config["disabled_steps_wd_old"] = file_disabled_wo
            changed = True

    if os.path.exists(KORDINAT_CREATE_ACCOUNT_FILE):
        steps_ca = get_kordinat_steps_from_file(KORDINAT_CREATE_ACCOUNT_FILE)
        file_disabled_ca = [s['id'] for s in steps_ca if s['is_off']]
        current_disabled_ca = config.get("disabled_steps_create_account", [])
        if sorted([str(x) for x in current_disabled_ca]) != sorted([str(x) for x in file_disabled_ca]):
            config["disabled_steps_create_account"] = file_disabled_ca
            changed = True

    if os.path.exists(KORDINAT_QRIS_MORPH_FILE):
        steps_qm = get_kordinat_steps_from_file(KORDINAT_QRIS_MORPH_FILE)
        file_disabled_qm = [s['id'] for s in steps_qm if s['is_off']]
        current_disabled_qm = config.get("disabled_steps_qris_morph", [])
        if sorted([str(x) for x in current_disabled_qm]) != sorted([str(x) for x in file_disabled_qm]):
            config["disabled_steps_qris_morph"] = file_disabled_qm
            changed = True

    if changed:
        save_config(config)

def update_kordinat_txt_step_file(filepath, target_step_id, set_off):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
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

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def update_all_kordinat_txt_steps_file(filepath, set_off):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
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
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def print_menu():
    clear_screen()
    print("=========================================================")
    print("   BOT ADB BITGET WALLET (WD XLM, BUAT AKUN & QRIS MORPH)")
    print("=========================================================")

    sync_kordinat_and_config()
    config = load_config()
    addr = config.get('alamat_wd', '')
    addr_disp = f"{addr[:15]}...{addr[-5:]}" if len(addr) > 20 else addr

    # Step WD Baru
    steps_wb = get_kordinat_steps_from_file(KORDINAT_WD_BARU_FILE)
    disabled_wb = config.get('disabled_steps_wd_baru', config.get('disabled_steps', []))
    disabled_wb_str = [str(x) for x in disabled_wb]
    dis_count_wb = len([s for s in steps_wb if s['is_off'] or s['id'] in disabled_wb or str(s['id']) in disabled_wb_str])
    status_wb = f"[{len(steps_wb) - dis_count_wb}/{len(steps_wb)} Step Aktif]"

    # Step WD Old
    steps_wo = get_kordinat_steps_from_file(KORDINAT_WD_OLD_FILE)
    disabled_wo = config.get('disabled_steps_wd_old', [])
    disabled_wo_str = [str(x) for x in disabled_wo]
    dis_count_wo = len([s for s in steps_wo if s['is_off'] or s['id'] in disabled_wo or str(s['id']) in disabled_wo_str])
    status_wo = f"[{len(steps_wo) - dis_count_wo}/{len(steps_wo)} Step Aktif]"

    # Step Create Account
    steps_ca = get_kordinat_steps_from_file(KORDINAT_CREATE_ACCOUNT_FILE)
    disabled_ca = config.get('disabled_steps_create_account', [])
    disabled_ca_str = [str(x) for x in disabled_ca]
    dis_count_ca = len([s for s in steps_ca if s['is_off'] or s['id'] in disabled_ca or str(s['id']) in disabled_ca_str])
    status_ca = f"[{len(steps_ca) - dis_count_ca}/{len(steps_ca)} Step Aktif]"

    # Step QRIS Morph
    steps_qm = get_kordinat_steps_from_file(KORDINAT_QRIS_MORPH_FILE)
    disabled_qm = config.get('disabled_steps_qris_morph', [])
    disabled_qm_str = [str(x) for x in disabled_qm]
    dis_count_qm = len([s for s in steps_qm if s['is_off'] or s['id'] in disabled_qm or str(s['id']) in disabled_qm_str])
    status_qm = f"[{len(steps_qm) - dis_count_qm}/{len(steps_qm)} Step Aktif]"
    cur_nom = int(config.get('default_qris_nominal', 18501))
    nom_display = f"{cur_nom:,}".replace(",", ".")

    # Multi IMAP accounts count
    imap_accounts = config.get("email_otp_accounts", [])
    imap_count_disp = f"[{len(imap_accounts)} Akun Terdaftar]"

    # Wallet Phrase File
    avail_wf = get_available_wallet_files()
    active_wf = config.get('active_wallet_file')
    if not active_wf and avail_wf:
        active_wf = avail_wf[0]
        config['active_wallet_file'] = active_wf
        save_config(config)
    phrases = load_wallet_phrases(active_wf) if active_wf else []
    wf_disp = f"{active_wf} ({len(phrases)} Frasa)" if active_wf else "[Kosong]"

    print(f"[*] Address WD Saat Ini : {addr_disp}")
    print(f"[*] PIN Saat Ini        : {config.get('pin')}")
    print(f"[*] File Wallet Mnemonic: {wf_disp}")
    print(f"[*] Clone / Akun Awal   : Akun ke-{config.get('start_index', 1)}")
    print(f"[*] Step WD (Mode Baru) : {status_wb}")
    print(f"[*] Step WD (Mode Old)  : {status_wo}")
    print(f"[*] Step Bot Buat Akun  : {status_ca}")
    print(f"[*] Step QRIS Morph     : {status_qm} (Rp {nom_display})")
    print(f"[*] Multi-IMAP Email    : {imap_count_disp}")
    print("=========================================================")
    print(" [1] MULAI BOT WD XLM - MODE BARU (IMPORT PROFIL TANPA AUTH)")
    print(" [2] MULAI BOT WD XLM - MODE OLD (TEMPEL AUTH GOOGLE)")
    print(" [3] MULAI BOT AUTO BUAT AKUN BITGET (LOOP)")
    print(f" [4] MULAI BOT QRIS MORPH CASHBACK (Rp {nom_display} -> TEBAR -> CLAIM)")
    print(" [5] MODE MANUAL / REKAM DELAY (SEMUA SCRIPT)")
    print(" [6] GANTI PENGATURAN (PIN, ADDRESS WD, FILE WALLET & CLONE)")
    print(" [7] ON/OFF STEP KOORDINAT BOT (PILIH SCRIPT)")
    print(" [8] PENGATURAN MULTI-IMAP EMAIL & OTP")
    print(" [9] PENGATURAN RESOLUSI & DPI LAYAR HP")
    if IS_TERMUX:
        print(" [A] KONEK ADB LOKAL (WIRELESS DEBUGGING)")
        print(" [D] INSTALL DEPENDENCIES & PENGATURAN DEVELOPER")
    else:
        print(" [A] KONEK ADB & SCRCPY (KHUSUS PC)")
        print(" [W] BUKA WEB UI DASHBOARD (BROWSER)")
    print(" [R] RESTART MENU UTAMA")
    print(" [0] EXIT")
    print("=========================================================")

def ganti_pengaturan():
    config = load_config()
    print("\n--- GANTI PENGATURAN ---")
    print("Kosongkan lalu tekan Enter jika tidak ingin mengubah data.")

    baru_address = input(f"Address WD ({config.get('alamat_wd')}): ").strip()
    if baru_address != "":
        config['alamat_wd'] = baru_address

    baru_pin = input(f"PIN Baru ({config.get('pin')}): ").strip()
    if baru_pin != "":
        if not baru_pin.isdigit():
            print("ERROR: PIN harus berupa angka!")
        else:
            config['pin'] = baru_pin

    baru_ref = input(f"Master Referral Code ({config.get('master_referral_code', 'JtzeyDtC')}): ").strip()
    if baru_ref != "":
        config['master_referral_code'] = baru_ref
        config['current_referral_code'] = baru_ref

    # Pilih file wallet
    print("\n--- PILIH FILE WALLET (DATA WALLET BITGET) ---")
    files = get_available_wallet_files()
    cur_wf = config.get("active_wallet_file", files[0] if files else "")
    for i, f in enumerate(files, start=1):
        mark = " [AKTIF]" if f == cur_wf else ""
        print(f"  {i}. {f}{mark}")
    pil_wf = input(f"Pilih nomor file (Enter untuk tetap '{cur_wf}'): ").strip()
    if pil_wf.isdigit() and 1 <= int(pil_wf) <= len(files):
        config["active_wallet_file"] = files[int(pil_wf) - 1]
        print(f"[*] File wallet diubah ke: {config['active_wallet_file']}")

    config['start_index'] = prompt_number_with_arrows(
        "Nomor Akun / Clone Awal [Panah Atas/Bawah | Ketik]:",
        default_val=config.get('start_index', 1),
        min_val=0
    )

    save_config(config)
    print("\n[!] Pengaturan berhasil disimpan!")
    input("Tekan Enter untuk kembali ke menu...")

def menu_imap_settings():
    while True:
        clear_screen()
        config = load_config()
        accounts = config.get("email_otp_accounts", [])

        print("=========================================================")
        print("          PENGATURAN MULTI-IMAP EMAIL & OTP              ")
        print("=========================================================")
        print(f"  Total Akun IMAP Terdaftar: {len(accounts)}")
        print("---------------------------------------------------------")
        for i, acc in enumerate(accounts, start=1):
            em = acc.get("email", "")
            srv = acc.get("imap_server", "imap.gmail.com")
            status = "[ ON ]" if acc.get("enabled", True) else "[OFF ]"
            print(f"  {i:>2}. Slot #{i} {status} {em:<25} ({srv})")
        print("---------------------------------------------------------")
        print("1. Tambah Akun IMAP Baru")
        print("2. Edit / Toggle ON/OFF / Hapus Akun IMAP")
        print("3. Impor & Sync dari core/emails.txt")
        print("4. Uji Coba Konek & Fetch OTP untuk Akun IMAP")
        print("0. Kembali ke Menu Utama")
        print("=========================================================")

        pil = input("Pilih menu (0-4): ").strip()

        if pil == '1':
            print("\n--- TAMBAH AKUN IMAP BARU ---")
            em = input("Alamat Email : ").strip()
            if not em:
                continue
            pw = input("Password IMAP / App Password : ").strip()
            srv = input("Server IMAP (Default auto-detect / imap.gmail.com): ").strip()
            port_str = input("Port IMAP (Default 993): ").strip()

            port = int(port_str) if port_str.isdigit() else 993
            if not srv:
                domain = em.split("@")[-1].lower() if "@" in em else ""
                if "outlook" in domain or "hotmail" in domain:
                    srv = "outlook.office365.com"
                elif "rambler" in domain:
                    srv = "imap.rambler.ru"
                elif "firstmail" in domain:
                    srv = "imap.firstmail.ltd"
                else:
                    srv = "imap.gmail.com"

            new_acc = {
                "id": f"slot_{len(accounts) + 1}",
                "name": f"Slot {len(accounts) + 1}",
                "email": em,
                "password": pw,
                "imap_server": srv,
                "imap_port": port,
                "enabled": True
            }
            accounts.append(new_acc)
            config["email_otp_accounts"] = accounts
            save_config(config)
            print(f"\n[V] Akun IMAP {em} berhasil ditambahkan!")
            time.sleep(1.2)

        elif pil == '2':
            if not accounts:
                print("\n[!] Belum ada akun IMAP terdaftar.")
                time.sleep(1)
                continue

            idx_str = input(f"\nMasukkan nomor slot akun untuk diedit (1-{len(accounts)}): ").strip()
            if idx_str.isdigit():
                idx = int(idx_str) - 1
                if 0 <= idx < len(accounts):
                    acc = accounts[idx]
                    print(f"\nEdit Slot #{idx+1} [{acc['email']}]:")
                    print("1. Toggle ON / OFF Status")
                    print("2. Ubah Password / App Password")
                    print("3. Hapus Akun ini")
                    sub = input("Pilih (1-3): ").strip()

                    if sub == '1':
                        acc['enabled'] = not acc.get('enabled', True)
                        print(f"[V] Status {acc['email']} diubah ke: {'ON' if acc['enabled'] else 'OFF'}")
                    elif sub == '2':
                        npw = input("Masukkan Password Baru: ").strip()
                        if npw:
                            acc['password'] = npw
                            print("[V] Password berhasil diperbarui!")
                    elif sub == '3':
                        accounts.pop(idx)
                        print(f"[!] Akun Slot #{idx+1} berhasil dihapus!")

                    config["email_otp_accounts"] = accounts
                    save_config(config)
                    time.sleep(1)

        elif pil == '3':
            if os.path.exists(EMAILS_FILE):
                with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]

                count_added = 0
                for i, line in enumerate(lines, start=1):
                    if '|' in line:
                        em, pw = line.split('|', 1)
                        em, pw = em.strip(), pw.strip()
                        if em and pw and not any(a.get("email") == em for a in accounts):
                            domain = em.split("@")[-1].lower() if "@" in em else ""
                            srv = "outlook.office365.com" if "outlook" in domain else ("imap.rambler.ru" if "rambler" in domain else "imap.gmail.com")
                            accounts.append({
                                "id": f"slot_{len(accounts) + 1}",
                                "name": f"Slot {len(accounts) + 1}",
                                "email": em,
                                "password": pw,
                                "imap_server": srv,
                                "imap_port": 993,
                                "enabled": True
                            })
                            count_added += 1

                config["email_otp_accounts"] = accounts
                save_config(config)
                print(f"\n[V] Berhasil mengimpor {count_added} akun baru dari core/emails.txt!")
            else:
                print(f"\n[!] File {EMAILS_FILE} tidak ditemukan!")
            time.sleep(1.5)

        elif pil == '4':
            if not accounts:
                print("\n[!] Belum ada akun IMAP terdaftar.")
                time.sleep(1)
                continue

            idx_str = input(f"\nMasukkan nomor slot akun untuk diuji (1-{len(accounts)}): ").strip()
            if idx_str.isdigit():
                idx = int(idx_str) - 1
                if 0 <= idx < len(accounts):
                    acc = accounts[idx]
                    reader = EmailOTPReader(acc['email'], acc['password'], imap_server=acc.get('imap_server'), imap_port=acc.get('imap_port', 993))
                    
                    print(f"\n[*] Menguji koneksi IMAP untuk {acc['email']}...")
                    res = reader.test_connection()
                    print(f"    Status Login: {res.get('message') or res.get('error')}")

                    if res.get("success"):
                        print("[*] Mencari OTP email Bitget terbaru di Inbox...")
                        res_otp = reader.get_latest_otp(timeout=15)
                        if res_otp.get("success"):
                            print(f"\n[V] SUKSES! Ditemukan OTP: {res_otp.get('otp')} (Subject: {res_otp.get('subject')})")
                        else:
                            print(f"\n[-] {res_otp.get('error')}")

                    input("\nTekan Enter untuk melanjutkan...")

        elif pil == '0':
            break

def execute_toggle_steps_logic(target_file, config_key):
    while True:
        sync_kordinat_and_config()
        config = load_config()
        disabled = config.get(config_key, [])
        disabled_str = [str(x) for x in disabled]
        steps = get_kordinat_steps_from_file(target_file)
        clear_screen()
        file_name = os.path.basename(target_file)
        print("=========================================================")
        print(f"     PENGATURAN ON/OFF STEP KOORDINAT ({file_name})     ")
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
        print("  0  = Kembali ke Menu Sebelumnya")
        print("=========================================================")
        pil = input("Masukkan nomor step untuk toggle (atau A/D/0): ").strip().upper()

        if pil == '0':
            break
        elif pil == 'A':
            config[config_key] = []
            save_config(config)
            update_all_kordinat_txt_steps_file(target_file, set_off=False)
            print(f"[V] Semua step DIAKTIFKAN di {file_name}!")
            time.sleep(1)
        elif pil == 'D':
            config[config_key] = [s['id'] for s in steps]
            save_config(config)
            update_all_kordinat_txt_steps_file(target_file, set_off=True)
            print(f"[!] Semua step DINONAKTIFKAN di {file_name}!")
            time.sleep(1)
        elif pil.isdigit():
            idx_pil = int(pil) - 1
            if 0 <= idx_pil < len(steps):
                step = steps[idx_pil]
                s_id = step['id']
                is_currently_off = step['is_off'] or s_id in disabled or str(s_id) in disabled_str
                new_off_state = not is_currently_off

                if new_off_state:
                    if s_id not in disabled and str(s_id) not in disabled_str:
                        disabled.append(s_id)
                    update_kordinat_txt_step_file(target_file, s_id, set_off=True)
                    print(f"[!] Step {s_id} [{step['name']}] -> OFF")
                else:
                    disabled = [x for x in disabled if x != s_id and str(x) != str(s_id)]
                    update_kordinat_txt_step_file(target_file, s_id, set_off=False)
                    print(f"[V] Step {s_id} [{step['name']}] -> ON")

                config[config_key] = disabled
                save_config(config)
                time.sleep(0.6)
            else:
                print("Nomor tidak valid!")
                time.sleep(1)
        else:
            print("Pilihan tidak dikenali!")
            time.sleep(1)

def menu_toggle_steps():
    while True:
        clear_screen()
        print("=========================================================")
        print("         PILIH SCRIPT KOORDINAT YANG INGIN DI-TOGGLE     ")
        print("=========================================================")
        print(" [1] STEP WD XLM MODE BARU (kordinat_wd_baru.txt)")
        print(" [2] STEP WD XLM MODE OLD (kordinat_wd_old.txt)")
        print(" [3] STEP BOT BUAT AKUN BITGET (kordinat_create_account.txt)")
        print(" [4] STEP BOT QRIS MORPH CASHBACK (kordinat_qris_morph.txt)")
        print(" [0] Kembali ke Menu Utama")
        print("=========================================================")
        pil = get_key_press(" Masukkan pilihan Anda [0-4]: ").strip().lower()

        if pil == '1':
            execute_toggle_steps_logic(KORDINAT_WD_BARU_FILE, "disabled_steps_wd_baru")
        elif pil == '2':
            execute_toggle_steps_logic(KORDINAT_WD_OLD_FILE, "disabled_steps_wd_old")
        elif pil == '3':
            execute_toggle_steps_logic(KORDINAT_CREATE_ACCOUNT_FILE, "disabled_steps_create_account")
        elif pil == '4':
            execute_toggle_steps_logic(KORDINAT_QRIS_MORPH_FILE, "disabled_steps_qris_morph")
        elif pil in ('0', 'q', 'enter'):
            break

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
    print("2. HANYA BUKA LAYAR (SCRCPY)")
    print("3. KONEK ADB NIRKABEL MANUAL (INPUT IP)")
    print("4. AUTO-SETUP WIRELESS SAJA (TANPA SCRCPY)")
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
            detected_ip = detect_device_wifi_ip(usb_dev)

            wireless_ready = False
            if detected_ip:
                print(f"[+] Wi-Fi HP aktif. IP terdeteksi: {detected_ip}")
                config["last_wifi_ip"] = detected_ip
                save_config(config)

                os.system(f"adb -s {usb_dev} tcpip 5555")
                time.sleep(1)

                if is_port_reachable(detected_ip, 5555, timeout=1.5):
                    os.system(f"adb connect {detected_ip}:5555")
                    wireless_ready = True
                else:
                    print(f"[-] Port {detected_ip}:5555 tidak merespons.")
            else:
                print("[*] Wi-Fi HP tidak aktif.")

            if wireless_ready:
                print("\n[V] BERHASIL TERSAMBUNG KE ADB WI-FI!")
                print("[!] KABEL USB SEKARANG SUDAH BISA DICABUT KAPAN SAJA!")
                launch_mirror_screen(f"-s {detected_ip}:5555")
            else:
                launch_mirror_screen(f"-s {usb_dev}")
        else:
            if last_ip and is_port_reachable(last_ip, 5555, timeout=1.5):
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
            os.system(f'adb connect {clean_ip}')
            config["last_wifi_ip"] = ip.split(":")[0]
            save_config(config)

    elif pil == '4':
        usb_dev = get_usb_device()
        if not usb_dev:
            input("Tekan Enter jika KABEL USB SUDAH TERSAMBUNG...")
            usb_dev = get_usb_device()

        if not usb_dev:
            print("[!] Perangkat USB tidak terdeteksi.")
            input("Tekan Enter untuk kembali...")
        else:
            detected_ip = detect_device_wifi_ip(usb_dev)
            os.system(f"adb -s {usb_dev} tcpip 5555")
            time.sleep(1)

            if detected_ip:
                config["last_wifi_ip"] = detected_ip
                save_config(config)
                if is_port_reachable(detected_ip, 5555, timeout=1.5):
                    os.system(f"adb connect {detected_ip}:5555")
                    print("\n[V] SUKSES! Kabel USB sekarang sudah bisa dicabut!")
            input("Tekan Enter untuk kembali...")

    elif pil == '5':
        ip_port = input("Masukkan IP:PORT Pairing (misal 192.168.x.x:35612): ").strip()
        code = input("Masukkan 6 Digit Kode Pairing: ").strip()
        if ip_port and code:
            os.system(f'adb pair {ip_port} {code}')

    if pil in ['1', '2', '3', '4', '5']:
        input("\nProses selesai. Tekan Enter untuk kembali ke menu...")

def menu_manual_rekam():
    wd_script = os.path.join(CORE_DIR, 'wd_xlm.py')
    ca_script = os.path.join(CORE_DIR, 'create_account.py')
    qris_script = os.path.join(CORE_DIR, 'qris_morph.py')

    while True:
        clear_screen()
        print("=========================================================")
        print("      MODE MANUAL STEP-BY-STEP / REKAM DELAY BOT         ")
        print("=========================================================")
        print(" [1] REKAM DELAY - WD XLM (MODE BARU TANPA AUTH)")
        print(" [2] STEP MANUAL - WD XLM (MODE BARU TANPA AUTH)")
        print(" [3] REKAM DELAY - WD XLM (MODE OLD TEMPEL AUTH)")
        print(" [4] STEP MANUAL - WD XLM (MODE OLD TEMPEL AUTH)")
        print(" [5] REKAM DELAY - BOT BUAT AKUN BITGET")
        print(" [6] STEP MANUAL - BOT BUAT AKUN BITGET")
        print(" [7] REKAM DELAY - BOT QRIS MORPH CASHBACK")
        print(" [8] STEP MANUAL - BOT QRIS MORPH CASHBACK")
        print(" [0] Kembali ke Menu Utama")
        print("=========================================================")
        sub = get_key_press(" Masukkan pilihan Anda [0-8]: ").strip().lower()

        if sub == '1':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> REKAM DELAY HP - WD XLM (MODE BARU) <<<\n")
            subprocess.run([sys.executable, wd_script, '--rekam'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai rekam. Tekan sembarang tombol untuk kembali...")
        elif sub == '2':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> STEP-BY-STEP MANUAL - WD XLM (MODE BARU) <<<\n")
            subprocess.run([sys.executable, wd_script, '--manual'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai. Tekan sembarang tombol untuk kembali...")
        elif sub == '3':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> REKAM DELAY HP - WD XLM (MODE OLD) <<<\n")
            subprocess.run([sys.executable, wd_script, '--old', '--rekam'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai rekam. Tekan sembarang tombol untuk kembali...")
        elif sub == '4':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> STEP-BY-STEP MANUAL - WD XLM (MODE OLD) <<<\n")
            subprocess.run([sys.executable, wd_script, '--old', '--manual'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai. Tekan sembarang tombol untuk kembali...")
        elif sub == '5':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> REKAM DELAY HP - BOT BUAT AKUN BITGET <<<\n")
            subprocess.run([sys.executable, ca_script, '--rekam'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai rekam. Tekan sembarang tombol untuk kembali...")
        elif sub == '6':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> STEP-BY-STEP MANUAL - BOT BUAT AKUN BITGET <<<\n")
            subprocess.run([sys.executable, ca_script, '--manual'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai. Tekan sembarang tombol untuk kembali...")
        elif sub == '7':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> REKAM DELAY HP - BOT QRIS MORPH CASHBACK <<<\n")
            subprocess.run([sys.executable, qris_script, '--rekam'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai rekam. Tekan sembarang tombol untuk kembali...")
        elif sub == '8':
            record_and_apply_bot_screen(silent=True)
            clear_screen()
            print(">>> STEP-BY-STEP MANUAL - BOT QRIS MORPH CASHBACK <<<\n")
            subprocess.run([sys.executable, qris_script, '--manual'], cwd=PROJECT_ROOT)
            wait_any_key("\n Selesai. Tekan sembarang tombol untuk kembali...")
        elif sub in ('0', 'q', 'enter'):
            break

def main():
    wd_script = os.path.join(CORE_DIR, 'wd_xlm.py')
    ca_script = os.path.join(CORE_DIR, 'create_account.py')
    qris_script = os.path.join(CORE_DIR, 'qris_morph.py')
    konek_script = os.path.join(PROJECT_ROOT, 'termux', 'konek_adb.py')

    register_auto_restore()
    record_and_apply_bot_screen(silent=True)

    try:
        while True:
            print_menu()
            pilihan = get_key_press(" Masukkan pilihan Anda [0-9 / A / W / R] (Tekan Tombol Langsung): ").strip().lower()

            if pilihan == '1':
                record_and_apply_bot_screen(silent=True)
                clear_screen()
                print(">>> MENJALANKAN BOT WD XLM — MODE BARU (IMPORT PROFIL TANPA AUTH) <<<\n")
                subprocess.run([sys.executable, wd_script], cwd=PROJECT_ROOT)
                wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu...")

            elif pilihan == '2':
                record_and_apply_bot_screen(silent=True)
                clear_screen()
                print(">>> MENJALANKAN BOT WD XLM — MODE OLD (TEMPEL AUTH GOOGLE) <<<\n")
                subprocess.run([sys.executable, wd_script, '--old'], cwd=PROJECT_ROOT)
                wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu...")

            elif pilihan == '3':
                record_and_apply_bot_screen(silent=True)
                clear_screen()
                print(">>> MENJALANKAN BOT AUTO BUAT AKUN BITGET <<<\n")
                subprocess.run([sys.executable, ca_script], cwd=PROJECT_ROOT)
                wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu...")

            elif pilihan == '4':
                record_and_apply_bot_screen(silent=True)
                clear_screen()
                print(">>> MENJALANKAN BOT QRIS MORPH CASHBACK <<<\n")
                subprocess.run([sys.executable, qris_script], cwd=PROJECT_ROOT)
                wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu...")

            elif pilihan == '5':
                menu_manual_rekam()

            elif pilihan == '6':
                ganti_pengaturan()

            elif pilihan == '7':
                menu_toggle_steps()

            elif pilihan == '8':
                menu_imap_settings()

            elif pilihan == '9':
                menu_resolusi_layar()

            elif pilihan in ('a', '10'):
                if IS_TERMUX:
                    clear_screen()
                    print("=========================================================")
                    print("SYARAT: Nyalakan 'Proses Debug Nirkabel' di Pengaturan Developer HP.")
                    print("=========================================================")
                    subprocess.run([sys.executable, konek_script], cwd=PROJECT_ROOT)
                    record_and_apply_bot_screen(silent=True)
                    wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu...")
                else:
                    konek_adb_scrcpy()
                    record_and_apply_bot_screen(silent=True)

            elif pilihan in ('w', '11') and not IS_TERMUX:
                clear_screen()
                print("=========================================================")
                print("         MEMBUKA WEB UI DASHBOARD (BROWSER)              ")
                print("=========================================================")
                print("  URL : http://127.0.0.1:5000                            ")
                print("  Tekan Ctrl+C di terminal ini jika ingin keluar Web UI. ")
                print("=========================================================")
                if os.name == 'nt':
                    os.system('start "" "http://127.0.0.1:5000"')
                server_script = os.path.join(CORE_DIR, 'server.py')
                try:
                    subprocess.run([sys.executable, server_script], cwd=PROJECT_ROOT)
                except KeyboardInterrupt:
                    pass
                wait_any_key("\n Web UI selesai. Tekan sembarang tombol untuk kembali...")

            elif pilihan in ('d', '11') and IS_TERMUX:
                clear_screen()
                print("[*] Memperbarui dependensi & Membuka Pengaturan Developer...")
                subprocess.run('pkg update -y && pkg install python nmap android-tools -y', shell=True, cwd=PROJECT_ROOT)
                os.system('am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS')
                wait_any_key("\n Selesai. Tekan sembarang tombol untuk kembali ke menu...")

            elif pilihan in ('r', 'restart'):
                clear_screen()
                print("[*] Merestart ulang sistem Menu Utama...")
                time.sleep(0.3)
                continue

            elif pilihan in ('0', 'q', 'exit'):
                clear_screen()
                print("[*] Menutup bot dan memulihkan resolusi layar HP...")
                restore_recorded_screen(silent=False)
                print("Keluar dari program. Terima kasih!")
                break
                sys.exit(0)

            else:
                print("Pilihan tidak valid!")
                time.sleep(0.7)
    finally:
        restore_recorded_screen(silent=True)

if __name__ == "__main__":
    main()
