import subprocess
import time
import os
import platform
import sys
import json
import atexit
import re

# Root Direktori Proyek
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore
)


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
REKAM_MODE  = "--rekam"  in sys.argv

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


DISABLED_STEPS = []

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

    # Ekstrak step id (misal 0, 1, 2.1, 11) dan deskripsi
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

def is_step_enabled(step_item):
    """
    Cek apakah step tertentu aktif.
    Step dianggap NONAKTIF jika:
    1. Ditandai 'OFF' langsung pada judul di kordinat.txt (step_item['is_off']), ATAU
    2. Terdaftar di disabled_steps pada config.json.
    """
    if step_item.get('is_off', False):
        return False
    step_id = step_item.get('id')
    return step_id not in DISABLED_STEPS and str(step_id) not in [str(x) for x in DISABLED_STEPS]

def parse_kordinat_file(filepath=KORDINAT_FILE):
    """Membaca dan mem-parsing seluruh langkah dan perintah ADB dari kordinat.txt."""
    if not os.path.exists(filepath):
        print(f"[!] Error: File koordinat {filepath} tidak ditemukan!")
        sys.exit(1)

    steps = []
    current_step = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue

            header = parse_step_header(stripped)
            if header:
                current_step = {
                    'id': header['id'],
                    'name': header['name'],
                    'full_title': header['full_title'],
                    'is_off': header['is_off'],
                    'commands': []
                }
                steps.append(current_step)
                continue

            if stripped.startswith('#') or stripped.startswith('---'):
                continue

            if current_step is not None:
                current_step['commands'].append(stripped)

    return steps

def update_sleep_in_kordinat(step_id, new_sleep_value, filepath=KORDINAT_FILE):
    """
    Menulis ulang nilai sleep terakhir sebuah step di kordinat.txt
    dengan nilai delay hasil rekaman user (dibulatkan 1 desimal).
    Jika step tidak punya 'sleep' sama sekali, tambahkan di akhir block step.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_val = f"{round(float(new_sleep_value), 1)}"

    # Temukan batas awal dan akhir block step target
    block_start = None
    block_end   = None
    in_target   = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        header = parse_step_header(stripped)
        if header is not None:
            if in_target:
                # Masuk ke step berikutnya — tutup block sebelumnya
                block_end = i
                break
            if str(header['id']) == str(step_id):
                block_start = i
                in_target   = True
        elif in_target and (stripped.startswith('---') or stripped == ''):
            # Pemisah / baris kosong — akhir block
            block_end = i
            break

    if block_start is None:
        return  # step tidak ditemukan, tidak ubah apapun

    if block_end is None:
        block_end = len(lines)

    # Cari sleep TERAKHIR di dalam block tersebut
    last_sleep_idx = None
    for i in range(block_start, block_end):
        parts = lines[i].strip().split()
        if parts and parts[0].lower() == 'sleep':
            last_sleep_idx = i

    if last_sleep_idx is not None:
        # Ganti nilai sleep-nya
        indent = lines[last_sleep_idx][:len(lines[last_sleep_idx]) - len(lines[last_sleep_idx].lstrip())]
        lines[last_sleep_idx] = f"{indent}sleep {new_val}\r\n"
    else:
        # Tidak ada sleep — sisipkan baris baru sebelum block_end
        lines.insert(block_end, f"sleep {new_val}\r\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def is_action_cmd(raw_cmd):
    """Kembalikan True jika perintah adalah aksi ADB (bukan sleep)."""
    parts = raw_cmd.strip().split()
    if not parts:
        return False
    if parts[0].lower() == 'sleep':
        return False
    return True


def execute_step_command(raw_cmd, context):
    """Mengeksekusi satu baris perintah ADB/macro dari kordinat.txt."""
    # Ganti variabel / placeholder dinamis
    cmd = raw_cmd
    cmd = cmd.replace("{ALAMAT_WD}", str(context.get("ALAMAT_WD", "")))
    cmd = cmd.replace("{ACCOUNT_NUM}", str(context.get("ACCOUNT_NUM", "")))
    cmd = cmd.replace("{PIN}", str(context.get("PIN", "")))

    parts = cmd.split()
    if not parts:
        return

    cmd_lower = parts[0].lower()

    # Perintah jeda waktu: "sleep 1.5"
    if cmd_lower == "sleep":
        dur = float(parts[1]) if len(parts) > 1 else 1.0
        stoppable_sleep(dur)
        return

    # Perintah PIN dinamis: "pin {PIN} 2.5" atau "dynamic_pin {PIN} 2.5"
    if cmd_lower in ("pin", "dynamic_pin"):
        pin_val = parts[1] if len(parts) > 1 else str(context.get("PIN", ""))
        final_jeda = float(parts[2]) if len(parts) > 2 else 2.5
        tap_dynamic_pin(pin_val, context.get("KEYPAD", {}), final_jeda=final_jeda)
        return

    # Perintah input tap: "input tap X Y"
    if len(parts) >= 4 and parts[0].lower() == "input" and parts[1].lower() == "tap":
        x, y = parts[2], parts[3]
        print(f"Tapping at ({x}, {y})")
        adb_command(f"shell input tap {x} {y}")
        return

    # Perintah input swipe: "input swipe X1 Y1 X2 Y2 [duration]"
    if len(parts) >= 6 and parts[0].lower() == "input" and parts[1].lower() == "swipe":
        print(f"Swiping from ({parts[2]}, {parts[3]}) to ({parts[4]}, {parts[5]})")
        adb_command(f"shell {cmd}")
        return

    # Perintah input text: "input text TEKS"
    if len(parts) >= 2 and parts[0].lower() == "input" and parts[1].lower() == "text":
        text_to_type = " ".join(parts[2:])
        if " " in text_to_type and not (text_to_type.startswith("'") and text_to_type.endswith("'")):
            text_to_type = text_to_type.replace(" ", "%s")
        print(f"Typing text: {text_to_type}")
        adb_command(f"shell input text '{text_to_type}'")
        return

    # Perintah input keyevent: "input keyevent 4" / "input keyevent 187"
    if len(parts) >= 2 and parts[0].lower() == "input" and parts[1].lower() == "keyevent":
        key = parts[2] if len(parts) > 2 else ""
        print(f"Keyevent: {key}")
        adb_command(f"shell {cmd}")
        return

    # Perintah umum lainnya (monkey, wm, am, pm, curl, dll)
    print(f"Executing: {cmd}")
    adb_command(f"shell {cmd}")

def run_rekam_delay(config):
    """
    Mode Rekam Delay:
    - Eksekusi semua ADB action per step (tap/swipe/text/keyevent/monkey/pin).
    - Perintah 'sleep' di dalam step diabaikan (tidak dijalankan).
    - Setelah seluruh action satu step selesai, stopwatch mulai.
    - User tekan ENTER ketika layar HP sudah siap untuk step berikutnya.
    - Elapsed time dicatat sebagai nilai delay baru dan langsung ditulis ke kordinat.txt.
    """
    global DISABLED_STEPS
    ALAMAT_WD = config.get("alamat_wd", "")
    PIN       = config.get("pin", "080808")
    KEYPAD    = config.get("keypad_coords", {})
    DISABLED_STEPS = config.get("disabled_steps", [])

    steps = parse_kordinat_file(KORDINAT_FILE)
    active_steps = [s for s in steps if is_step_enabled(s)]

    print(f"\n[*] Berhasil memuat {len(steps)} langkah ({len(active_steps)} aktif) dari core/kordinat.txt")
    print("""
=========================================================
               MODE REKAM DELAY AKTIF
=========================================================
  Cara kerja:
  1. Bot jalankan semua klik/swipe/action per step.
  2. Stopwatch dimulai segera setelah action selesai.
  3. Tekan ENTER saat layar HP sudah siap ke langkah
     berikutnya. Waktu akan otomatis disimpan ke
     core/kordinat.txt sebagai delay baru.
  4. Ketik 'S' + ENTER untuk SKIP step (delay tidak
     diubah untuk step tersebut).
  5. Ketik 'Q' + ENTER untuk BERHENTI merekam.

  Rekaman menggunakan 1 akun saja (clone ke-0).
  Setelah rekam, jalankan WD Otomatis (Menu 1).
=========================================================
""")
    input("--> Siapkan HP Anda, lalu tekan ENTER untuk mulai rekam...")

    context = {
        "ALAMAT_WD": ALAMAT_WD,
        "ACCOUNT_NUM": 0,
        "PIN": PIN,
        "KEYPAD": KEYPAD
    }

    recorded = {}

    for step in active_steps:
        step_id = step["id"]
        log_step(f"# {step['full_title']}")

        # Jalankan semua action (SKIP sleep agar tidak ada jeda otomatis)
        for cmd in step["commands"]:
            if not is_action_cmd(cmd):
                continue  # lewati sleep
            execute_step_command(cmd, context)

        # Mulai stopwatch
        t_start = time.time()
        prompt_msg = (
            f"\n  [REKAM] Selesai: \"{step['full_title']}\"\n"
            f"  Stopwatch berjalan... Tekan ENTER saat layar HP siap.\n"
            f"  (S=Skip rekam delay step ini | Q=Berhenti): "
        )
        user_key = input(prompt_msg).strip().lower()
        elapsed  = round(time.time() - t_start, 1)

        if user_key == 'q':
            print("\n[X] Rekaman dihentikan oleh pengguna.")
            break
        elif user_key == 's':
            print(f"  [--] Step {step_id} di-SKIP, delay lama dipertahankan.")
            continue

        # Pastikan minimal 0.3 detik agar bot tidak terlalu cepat
        elapsed = max(elapsed, 0.3)
        update_sleep_in_kordinat(step_id, elapsed)
        recorded[step_id] = elapsed
        print(f"  [V]  Delay step {step_id} direkam: {elapsed}s  -> disimpan ke kordinat.txt")

    print(f"\n=========================================================")
    print(f"  REKAMAN SELESAI — {len(recorded)} step delay diperbarui.")
    if recorded:
        print(f"  Ringkasan delay baru:")
        for sid, val in recorded.items():
            print(f"    Step {sid}: {val}s")
    print(f"=========================================================")
    print("  Jalankan WD Otomatis (Menu 1) untuk memakai delay baru.")
    print(f"=========================================================\n")


def run_bot(config):
    global DISABLED_STEPS
    # Konfigurasi Looping
    TOTAL_AKUN = config.get("total_akun", 5)
    ALAMAT_WD  = config.get("alamat_wd", "")
    PIN        = config.get("pin", "080808")
    KEYPAD     = config.get("keypad_coords", {})
    DISABLED_STEPS = config.get("disabled_steps", [])

    # Nomor Urut Awal untuk Penamaan di Google Authenticator (Default: 0)
    START_INDEX = config.get("start_index", 0)

    print(f"\n[?] Bot akan memproses {TOTAL_AKUN} akun sekaligus.")
    inp_start = input(f"[?] Mulai dari clone nomor berapa? (Tekan Enter untuk {START_INDEX}): ").strip()
    if inp_start.isdigit():
        START_INDEX = int(inp_start)

    # Baca file koordinat kordinat.txt
    steps = parse_kordinat_file(KORDINAT_FILE)
    print(f"[*] Berhasil memuat {len(steps)} langkah automasi dari core/kordinat.txt")

    # Sinkronisasi status OFF dari kordinat.txt ke config.json jika ada perbedaan
    file_disabled = [s['id'] for s in steps if s['is_off']]
    if sorted([str(x) for x in DISABLED_STEPS]) != sorted([str(x) for x in file_disabled]):
        DISABLED_STEPS = file_disabled
        config["disabled_steps"] = DISABLED_STEPS
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

        context = {
            "ALAMAT_WD": ALAMAT_WD,
            "ACCOUNT_NUM": current_account_num,
            "PIN": PIN,
            "KEYPAD": KEYPAD
        }

        for step in steps:
            step_id = step["id"]
            if not is_step_enabled(step):
                print(f"[SKIP] Step {step_id}: {step['name']}")
                continue

            log_step(f"# {step['full_title']}")
            for cmd in step["commands"]:
                execute_step_command(cmd, context)

            if MANUAL_MODE:
                print(f"\n[STEP-BY-STEP] Selesai: {step['full_title']}")
                user_key = input("--> Tekan ENTER untuk lanjut ke langkah berikutnya (atau 'Q' lalu Enter untuk berhenti): ").strip().lower()
                if user_key in ('q', 'exit'):
                    print("\n[X] Eksekusi dihentikan oleh pengguna.")
                    return

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
    
    # Jika dijalankan terpisah tanpa menu.py (standalone), bot mengelola sendiri resolusi
    is_standalone = os.environ.get("BOT_MANAGED_SCREEN") != "1"
    if is_standalone:
        register_auto_restore()
        record_and_apply_bot_screen()

    try:
        if REKAM_MODE:
            run_rekam_delay(config)
        else:
            run_bot(config)
    finally:
        if is_standalone:
            restore_recorded_screen()

if __name__ == "__main__":
    main()

