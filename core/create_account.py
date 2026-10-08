import subprocess
import time
import os
import platform
import sys
import json
import atexit
import re

# Root & Core Directory Setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat_create_account.txt')
ACCOUNTS_LOG_FILE = os.path.join(CORE_DIR, 'created_accounts.json')
EMAILS_FILE = os.path.join(CORE_DIR, 'emails.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore
)
from imap_helper import fetch_bitget_otp

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Setup path ADB untuk PC
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

if platform.system() == "Windows":
    import msvcrt

current_step_info = "Menyiapkan bot pembuatan akun..."

def log_step(text):
    global current_step_info
    current_step_info = text
    print(f"\n---> {text}")

MANUAL_MODE = "--manual" in sys.argv
REKAM_MODE  = "--rekam"  in sys.argv

def handle_pause(pause_reason="TOMBOL 'P' / CTRL+C DITEKAN", remaining_time=0):
    global current_step_info
    print(f"\n\n[!!!] PROGRAM DIPAUSE ({pause_reason}) [!!!]")
    print(f"[*] POSISI TERAKHIR: {current_step_info}")
    print("Silakan perbaiki posisi layar HP Anda jika diperlukan.")
    print(" --> Tekan ENTER atau CTRL+V untuk MELANJUTKAN")
    print(" --> Tekan 'Q' untuk BERHENTI / KELUAR")

    while True:
        if platform.system() == "Windows" and sys.stdin.isatty():
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                continue

            if ch in (b'\r', b'\n', b'\x16'):
                key_name = "Ctrl+V" if ch == b'\x16' else "ENTER"
                print(f"\n[>] Shortcut '{key_name}' terdeteksi! Melanjutkan proses dalam 1 detik...")
                time.sleep(1)
                print("GO!\n")
                return True
            elif ch in (b'q', b'Q', b'x', b'X'):
                print("\n[X] EKSEKUSI DIHENTIKAN OLEH PENGGUNA ('Q').")
                sys.exit(0)
        else:
            try:
                line = sys.stdin.readline().strip().lower()
            except KeyboardInterrupt:
                continue

            if line in ('q', 'quit', 'exit'):
                print("\n[X] EKSEKUSI DIHENTIKAN OLEH PENGGUNA ('Q').")
                sys.exit(0)
            else:
                print("\n[>] Melanjutkan proses...")
                return True

def prompt_manual_step(step_title):
    print(f"\n[STEP-BY-STEP] Selesai: {step_title}")
    sys.stdout.write("--> Tekan ENTER atau CTRL+V untuk lanjut ke langkah berikutnya (atau 'Q' untuk berhenti): ")
    sys.stdout.flush()

    if platform.system() == "Windows" and sys.stdin.isatty():
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                handle_pause("CTRL+C DITEKAN")
                sys.stdout.write("\n--> Tekan ENTER atau CTRL+V untuk lanjut ke langkah berikutnya (atau 'Q' untuk berhenti): ")
                sys.stdout.flush()
                continue

            if ch in (b'\r', b'\n', b' ', b'\x16'):
                key_label = "ENTER" if ch in (b'\r', b'\n', b' ') else "Ctrl+V"
                sys.stdout.write(f" [{key_label}]\n")
                sys.stdout.flush()
                return 'next'
            elif ch in (b'p', b'P'):
                handle_pause("TOMBOL 'P' DITEKAN")
                sys.stdout.write("\n--> Tekan ENTER atau CTRL+V untuk lanjut ke langkah berikutnya (atau 'Q' untuk berhenti): ")
                sys.stdout.flush()
            elif ch in (b'q', b'Q'):
                sys.stdout.write("q\n")
                sys.stdout.flush()
                return 'q'
    else:
        try:
            line = sys.stdin.readline().strip()
        except KeyboardInterrupt:
            handle_pause("CTRL+C DITEKAN")
            return prompt_manual_step(step_title)

        if line.lower() in ('q', 'quit', 'exit'):
            return 'q'
        return 'next'

def prompt_next_clone(next_account_num):
    print(f"\n=========================================================")
    print(f"--> Tekan ENTER atau CTRL+V untuk lanjut ke pembuatan akun clone berikutnya (ke-{next_account_num})")
    sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): ")
    sys.stdout.flush()

    if platform.system() == "Windows" and sys.stdin.isatty():
        buf = []
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                handle_pause("CTRL+C DITEKAN")
                print(f"\n--> Tekan ENTER atau CTRL+V untuk lanjut ke pembuatan akun clone berikutnya (ke-{next_account_num})")
                sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): {''.join(buf)}")
                sys.stdout.flush()
                continue

            if ch in (b'\r', b'\n', b'\x16'):
                key_label = "Ctrl+V" if ch == b'\x16' else "ENTER"
                if buf:
                    typed = "".join(buf).strip()
                    sys.stdout.write(f" [{key_label}]\n")
                    sys.stdout.flush()
                    if typed.isdigit():
                        return int(typed)
                    elif typed.lower() in ('q', 'quit', 'exit'):
                        return 'q'
                    return next_account_num
                else:
                    if ch == b'\x16':
                        sys.stdout.write("[Ctrl+V]\n")
                    else:
                        sys.stdout.write("\n")
                    sys.stdout.flush()
                    return next_account_num

            elif ch in (b'p', b'P') and not buf:
                handle_pause("TOMBOL 'P' DITEKAN")
                print(f"\n--> Tekan ENTER atau CTRL+V untuk lanjut ke pembuatan akun clone berikutnya (ke-{next_account_num})")
                sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): ")
                sys.stdout.flush()

            elif ch in (b'q', b'Q') and not buf:
                sys.stdout.write("q\n")
                sys.stdout.flush()
                return 'q'

            elif ch == b'\x08':
                if buf:
                    buf.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            else:
                try:
                    char = ch.decode('latin1')
                    if char.isprintable():
                        buf.append(char)
                        sys.stdout.write(char)
                        sys.stdout.flush()
                except Exception:
                    pass
    else:
        try:
            line = sys.stdin.readline().strip()
        except KeyboardInterrupt:
            handle_pause("CTRL+C DITEKAN")
            return prompt_next_clone(next_account_num)

        if line == "" or "\x16" in line:
            return next_account_num
        elif line.lower() in ('q', 'quit', 'exit'):
            return 'q'
        elif line.lower() in ('p', 'pause'):
            handle_pause("TOMBOL 'P' DITEKAN")
            return prompt_next_clone(next_account_num)
        elif line.isdigit():
            return int(line)
        else:
            return next_account_num

def stoppable_sleep(jeda):
    end_time = time.time() + jeda

    while time.time() < end_time:
        paused = False
        pause_reason = ""

        if platform.system() == "Windows" and sys.stdin.isatty():
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b'p', b'P', b'\x03'):
                        paused = True
                        pause_reason = "TOMBOL 'P' DITEKAN" if key in (b'p', b'P') else "CTRL+C DITEKAN"
                    elif key in (b'q', b'Q'):
                        print("\n\n[X] EKSEKUSI DIHENTIKAN OLEH PENGGUNA ('Q' DITEKAN).")
                        sys.exit(0)
            except KeyboardInterrupt:
                paused = True
                pause_reason = "CTRL+C DITEKAN"
        else:
            try:
                import select
                i, o, e = select.select([sys.stdin], [], [], 0)
                if i:
                    line = sys.stdin.readline().strip().lower()
                    if line in ('p', 'pause'):
                        paused = True
                        pause_reason = "TOMBOL 'P' DITEKAN"
                    elif line in ('q', 'exit'):
                        print("\n\n[X] EKSEKUSI DIHENTIKAN OLEH PENGGUNA ('Q' DITEKAN).")
                        sys.exit(0)
            except KeyboardInterrupt:
                paused = True
                pause_reason = "CTRL+C DITEKAN"
            except Exception:
                pass

        if paused:
            sisa_waktu = max(0, end_time - time.time())
            handle_pause(pause_reason, sisa_waktu)
            end_time = time.time() + sisa_waktu

        time.sleep(0.05)

ADB_PATH = "adb"

def adb_command(command):
    try:
        result = subprocess.run(
            f'"{ADB_PATH}" {command}' if platform.system() == "Windows" else f'{ADB_PATH} {command}',
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error executing ADB command: {e}")
        return ""

def tap(x, y, jeda=1.0):
    print(f" [*] Sentuh Koordinat ADB: ({x}, {y}) - Jeda {jeda}s")
    adb_command(f"shell input tap {x} {y}")
    stoppable_sleep(jeda)

def tap_rel(rx, ry, jeda=1.0, width=1080, height=2400):
    x_px = int(float(rx) * width)
    y_px = int(float(ry) * height)
    print(f" [*] Sentuh Rasio ADB: ({rx:.4f}, {ry:.4f}) -> Piksel ({x_px}, {y_px}) - Jeda {jeda}s")
    adb_command(f"shell input tap {x_px} {y_px}")
    stoppable_sleep(jeda)

def tap_slot(account_num, slot_coords, jeda=7.0):
    page = (account_num - 1) // 7
    slot_idx = str(((account_num - 1) % 7) + 1)

    print(f"[*] Smart Slot Selection: Akun ke-{account_num} -> Halaman {page + 1}, Slot #{slot_idx}")

    if page > 0:
        print(f"[*] Scrolling {page} kali ke bawah untuk mencapai halaman slot {page + 1}...")
        for _ in range(page):
            swipe(546, 1800, 546, 400, duration=1000, jeda=1.0)

    if slot_idx in slot_coords:
        coord = slot_coords[slot_idx]
        x, y = coord['x'], coord['y']
        print(f"[*] Mengetuk Slot #{slot_idx} di ({x}, {y}) - Jeda {jeda}s")
        tap(x, y, jeda=jeda)
    else:
        default_slots = {
            "1": (225, 391), "2": (228, 676), "3": (228, 962),
            "4": (221, 1268), "5": (221, 1550), "6": (232, 1832), "7": (225, 2118)
        }
        x, y = default_slots.get(slot_idx, (225, 391))
        print(f"[*] Mengetuk Fallback Slot #{slot_idx} di ({x}, {y}) - Jeda {jeda}s")
        tap(x, y, jeda=jeda)

def swipe(x1, y1, x2, y2, duration=500, jeda=1.0):
    print(f"Swiping from ({x1}, {y1}) to ({x2}, {y2}) - Waiting {jeda}s")
    adb_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    stoppable_sleep(jeda)

def input_text(text, jeda=1.0):
    print(f"Typing text: {text}")
    text = str(text).replace(' ', '%s')
    adb_command(f"shell input text '{text}'")
    stoppable_sleep(jeda)

def press_back(jeda=1.0):
    print(f"Pressing BACK - Waiting {jeda}s")
    adb_command("shell input keyevent 4")
    stoppable_sleep(jeda)

def open_recent_apps(jeda=2.0):
    print(f"Opening Recent Apps - Waiting {jeda}s")
    adb_command("shell input keyevent 187")
    stoppable_sleep(jeda)

def tap_dynamic_pin(pin_str, keypad_coords, final_jeda=2.5):
    print(f"Memasukkan PIN dinamis ({pin_str}) via koordinat sentuh...")
    for i, digit in enumerate(pin_str):
        if digit in keypad_coords:
            coord = keypad_coords[digit]
            x, y = coord['x'], coord['y']
            print(f" Digit [{digit}] -> Tap ({x}, {y})")
            adb_command(f"shell input tap {x} {y}")
            time.sleep(0.45)
        else:
            print(f" [!] Error: Koordinat untuk digit '{digit}' tidak ditemukan!")
    stoppable_sleep(final_jeda)

def get_email_for_account(account_num):
    if not os.path.exists(EMAILS_FILE):
        return None, None
    try:
        with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
        if not lines:
            return None, None
        idx = (account_num - 1) % len(lines)
        line = lines[idx]
        if '|' in line:
            parts = line.split('|', 1)
            return parts[0].strip(), parts[1].strip()
        else:
            return line.strip(), ""
    except Exception as e:
        print(f"[!] Error membaca emails.txt: {e}")
        return None, None

def get_adb_clipboard_text():
    out = adb_command("shell dumpsys clipboard")
    m = re.search(r"text/plain\s*\{\s*T:\s*([A-Za-z0-9]+)\s*\}", out)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"Text:\s*([A-Za-z0-9]+)", out, re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    m3 = re.search(r"\b([A-Za-z0-9]{6,12})\b", out)
    if m3:
        return m3.group(1).strip()
    return ""

def update_config_referral_code(new_code):
    config = load_config()
    config["current_referral_code"] = new_code
    config["referral_code"] = new_code
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[V] Kode referral untuk tuyul berikutnya berhasil diperbarui ke: {new_code}")
    except Exception as e:
        print(f"[!] Gagal update config.json referral: {e}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "pin": "080808",
        "master_referral_code": "JtzeyDtC",
        "current_referral_code": "JtzeyDtC",
        "referral_code": "JtzeyDtC",
        "imap_default_server": "imap.gmail.com",
        "imap_default_port": 993,
        "imap_use_ssl": True,
        "start_index": 1,
        "disabled_steps_create_account": []
    }

def update_config_start_index(next_index):
    config = load_config()
    config["start_index"] = next_index
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"[*] Update config.json: Clone berikutnya disetel ke-{next_index}")
    except Exception as e:
        print(f"[!] Gagal update config.json: {e}")

def log_created_account(account_num, status="SUCCESS", email_used=None, ref_used=None):
    data = []
    if os.path.exists(ACCOUNTS_LOG_FILE):
        try:
            with open(ACCOUNTS_LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = []

    entry = {
        "account_num": account_num,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "email": email_used or "N/A",
        "ref_used": ref_used or "N/A"
    }
    data.append(entry)

    try:
        with open(ACCOUNTS_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"[V] Account ke-{account_num} tercatat di core/created_accounts.json")
    except Exception as e:
        print(f"[!] Gagal mencatat log akun: {e}")

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
        "is_off": is_off
    }

def update_sleep_in_kordinat(target_step_id, new_sleep_val):
    if not os.path.exists(KORDINAT_FILE):
        return
    with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    current_step_id = None
    in_target_step = False

    for line in lines:
        stripped = line.strip()
        header = parse_step_header(stripped)
        if header:
            current_step_id = header["id"]
            in_target_step = (str(current_step_id) == str(target_step_id))
            new_lines.append(line)
            continue

        if in_target_step and stripped.startswith("sleep"):
            new_lines.append(f"sleep {new_sleep_val:.1f}\n")
            in_target_step = False
        else:
            new_lines.append(line)

    with open(KORDINAT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f"[*] Delay Step {target_step_id} berhasil diperbarui di kordinat_create_account.txt -> sleep {new_sleep_val:.1f}s")

def parse_and_execute_kordinat(account_num):
    if not os.path.exists(KORDINAT_FILE):
        print(f"[!] Error: File {KORDINAT_FILE} tidak ditemukan!")
        return False

    config = load_config()
    disabled_steps = config.get("disabled_steps_create_account", [])
    disabled_str = [str(x) for x in disabled_steps]
    keypad_coords = config.get("keypad_coords", {})
    slot_coords = config.get("clone_slot_coords", {})
    pin = config.get("pin", "080808")
    ref_code = config.get("current_referral_code") or config.get("referral_code", "JtzeyDtC")

    # Deteksi email & password IMAP untuk akun ini
    current_email, current_imap_pass = get_email_for_account(account_num)
    otp_requested_time = time.time()

    with open(KORDINAT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.split('--------------------------------------------------------------------------------')

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip() and not l.strip().startswith('#')]
        if not lines:
            continue

        header_line = lines[0]
        header = parse_step_header(header_line)

        if not header:
            continue

        step_id = header["id"]
        step_name = header["name"]

        if header["is_off"] or step_id in disabled_steps or str(step_id) in disabled_str:
            log_step(f"Step {step_id}. [{step_name}] -> DI-SKIP (STATUS OFF)")
            continue

        log_step(f"Step {step_id}. [{step_name}]")
        t_start_rec = time.time() if REKAM_MODE else None

        # Jika step ini adalah Minta Kode OTP Email, perbarui timestamp pemintaan OTP
        if "minta kode otp" in step_name.lower() or "kirim kode otp" in step_name.lower() or str(step_id) in ("24", "25"):
            otp_requested_time = time.time()

        for cmd in lines[1:]:
            cmd_lower = cmd.lower()
            jeda_act = 0.0 if REKAM_MODE else 0.5

            if cmd_lower.startswith("input slot_tap"):
                tap_slot(account_num, slot_coords, jeda=0.0 if REKAM_MODE else 7.0)

            elif cmd_lower.startswith("input type_kyc_email"):
                if current_email:
                    print(f"[*] Mengisi Email KYC Akun ke-{account_num}: {current_email}")
                    input_text(current_email, jeda=jeda_act)
                    # Sembunyikan Virtual Keyboard HP agar tombol 'Get verification code' terlihat & tidak ada spasi
                    adb_command("shell input keyevent 111") # ESCAPE
                    time.sleep(0.1 if REKAM_MODE else 0.3)
                    adb_command("shell input keyevent 4")   # BACK (Hide Keyboard)
                    time.sleep(0.1 if REKAM_MODE else 0.5)
                else:
                    print(f"[!] Warning: Email untuk akun ke-{account_num} tidak ditemukan di core/emails.txt")

            elif cmd_lower.startswith("input imap_fetch_and_type_otp"):
                if current_email and current_imap_pass:
                    imap_srv = config.get("imap_default_server", "imap.gmail.com")
                    imap_port = config.get("imap_default_port", 993)
                    use_ssl = config.get("imap_use_ssl", True)
                    
                    otp = fetch_bitget_otp(
                        email_user=current_email,
                        email_pass=current_imap_pass,
                        imap_server=imap_srv,
                        imap_port=imap_port,
                        use_ssl=use_ssl,
                        min_timestamp=otp_requested_time,
                        timeout=300
                    )
                    
                    if otp:
                        print(f"[V] [IMAP WATCHER SUCCESS] OTP TERBARU TERDETEKSI: {otp}")
                        print(f"[*] Menginput OTP {otp} ke Bitget Wallet (Keyevents & Paste)...")
                        
                        # 1. Tap tombol Paste melayang di layar (868, 315) jika ada
                        tap(868, 315, jeda=jeda_act)
                        
                        # 2. Ketik digit demi digit via ADB Keyevent (7 = '0', 8 = '1', ..., 16 = '9')
                        for ch in str(otp):
                            if ch.isdigit():
                                kc = 7 + int(ch)
                                adb_command(f"shell input keyevent {kc}")
                                time.sleep(0.05 if REKAM_MODE else 0.15)
                                
                        # 3. Fallback input text biasa & Paste Keyevent
                        adb_command("shell input keyevent 279") # Paste keyevent
                        input_text(otp, jeda=jeda_act)
                    else:
                        print(f"[!] Gagal mengambil OTP dari IMAP untuk {current_email}")
                else:
                    print(f"[!] Email/Password IMAP belum diatur untuk akun ke-{account_num} di emails.txt")

            elif cmd_lower.startswith("input copy_own_referral"):
                print("[*] Salin Kode Referral Tuyul Aktif...")
                # Tekan tombol salin kode di Bitget Wallet (misal tap tombol copy)
                adb_command("shell input keyevent 279") # Paste/Copy key event
                time.sleep(0.2 if REKAM_MODE else 1.0)
                clip_text = get_adb_clipboard_text()
                if clip_text:
                    print(f"[V] Kode referral tuyul ke-{account_num} terdeteksi dari clipboard: {clip_text}")
                    update_config_referral_code(clip_text)
                else:
                    print(f"[*] Clipboard kosong, menggunakan referral aktif: {ref_code}")

            elif cmd_lower.startswith("input tap_rel"):
                parts = cmd.split()
                if len(parts) >= 4:
                    rx, ry = float(parts[2]), float(parts[3])
                    tap_rel(rx, ry, jeda=jeda_act)

            elif cmd_lower.startswith("input tap") and not cmd_lower.startswith("input tap_rel"):
                parts = cmd.split()
                if len(parts) >= 4:
                    x, y = int(parts[2]), int(parts[3])
                    tap(x, y, jeda=jeda_act)

            elif cmd_lower.startswith("input swipe"):
                parts = cmd.split()
                if len(parts) >= 6:
                    x1, y1, x2, y2 = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                    dur = int(parts[6]) if len(parts) >= 7 else 500
                    swipe(x1, y1, x2, y2, duration=dur, jeda=jeda_act)

            elif cmd_lower.startswith("input text"):
                text_val = cmd[len("input text"):].strip()
                text_val = text_val.replace("{ACCOUNT_NUM}", str(account_num)).replace("{PIN}", pin).replace("{REFERRAL_CODE}", ref_code)
                if "{EMAIL}" in text_val:
                    text_val = text_val.replace("{EMAIL}", current_email or "")
                input_text(text_val, jeda=jeda_act)

            elif cmd_lower.startswith("input keyevent"):
                parts = cmd.split()
                if len(parts) >= 3:
                    code = parts[2]
                    if code == "4":
                        press_back(jeda=jeda_act)
                    elif code == "187":
                        open_recent_apps(jeda=jeda_act)
                    else:
                        adb_command(f"shell input keyevent {code}")
                        stoppable_sleep(jeda_act)

            elif cmd_lower.startswith("pin"):
                parts = cmd.split()
                jeda_pin = 0.2 if (REKAM_MODE or MANUAL_MODE) else (float(parts[2]) if len(parts) >= 3 else 2.5)
                tap_dynamic_pin(pin, keypad_coords, final_jeda=jeda_pin)

            elif cmd_lower.startswith("sleep"):
                parts = cmd.split()
                if len(parts) >= 2:
                    jeda = float(parts[1])
                    if REKAM_MODE:
                        sys.stdout.write("--> [REKAM DELAY] HP sedang loading... Tekan ENTER ketika tampilan HP Anda sudah SIAP / SELESAI loading... ")
                        sys.stdout.flush()

                        if platform.system() == "Windows" and sys.stdin.isatty():
                            msvcrt.getch()
                        else:
                            sys.stdin.readline()

                        measured = max(0.5, time.time() - (t_start_rec or time.time()))
                        print(f" [Tercatat: {measured:.1f}s]")
                        update_sleep_in_kordinat(step_id, measured)
                    elif MANUAL_MODE:
                        pass
                    else:
                        stoppable_sleep(jeda)

            elif cmd_lower.startswith("monkey"):
                adb_command(f"shell {cmd}")
                stoppable_sleep(1.0)

        if MANUAL_MODE:
            res = prompt_manual_step(f"Step {step_id} [{step_name}]")
            if res == 'q':
                print("\n[X] EKSEKUSI DIHENTIKAN OLEH PENGGUNA ('Q').")
                sys.exit(0)

    return True

def run_create_account_loop():
    register_auto_restore()
    record_and_apply_bot_screen()

    config = load_config()
    current_account = config.get("start_index", 1)

    print("\n=========================================================")
    print("      STARTING BITGET WALLET ACCOUNT CREATOR BOT         ")
    print("=========================================================")
    print(f" Master Referral Code  : {config.get('master_referral_code', 'JtzeyDtC')}")
    print(f" Current Referral Code : {config.get('current_referral_code', 'JtzeyDtC')}")
    if MANUAL_MODE:
        print(" MODE: STEP-BY-STEP MANUAL (ENTER = Lanjut step)")
    elif REKAM_MODE:
        print(" MODE: REKAM DELAY HP (ENTER = Catat delay)")
    else:
        print(" MODE: AUTOMATIC FULL LOOP")
    print(" (Tekan 'P' atau CTRL+C kapan saja untuk PAUSE)")
    print(" (Tekan 'Q' kapan saja untuk KELUAR)")
    print("=========================================================\n")

    while True:
        print(f"\n=========================================================")
        print(f"   MEMPROSES CREATION CLONE BITGET KE-{current_account}  ")
        print(f"=========================================================")

        success = parse_and_execute_kordinat(current_account)

        if success:
            config = load_config()
            cur_email, _ = get_email_for_account(current_account)
            log_created_account(
                current_account,
                status="SUCCESS",
                email_used=cur_email,
                ref_used=config.get("current_referral_code")
            )
            print(f"\n[V] AKUN CLONE KE-{current_account} BERHASIL SELESAI DIPROSES!")
            next_account = current_account + 1
            update_config_start_index(next_account)

            ans = prompt_next_clone(next_account)

            if ans == 'q':
                print("\n[X] KELUAR DARI BOT PEMBUATAN AKUN.")
                break
            elif isinstance(ans, int):
                current_account = ans
                update_config_start_index(current_account)
            else:
                current_account = next_account
        else:
            print(f"\n[!] PROSES AKUN KE-{current_account} GAGAL/DIHENTIKAN!")
            break

if __name__ == "__main__":
    try:
        run_create_account_loop()
    except KeyboardInterrupt:
        print("\n[!] Program dihentikan oleh pengguna (Ctrl+C).")
        sys.exit(0)
