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

USE_OLD_MODE = "--old" in sys.argv
if USE_OLD_MODE:
    KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat_wd_old.txt')
    CONFIG_DISABLED_KEY = "disabled_steps_wd_old"
    MODE_NAME = "BOT WD XLM - MODE OLD (TEMPEL AUTH GOOGLE)"
else:
    KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat_wd_baru.txt')
    CONFIG_DISABLED_KEY = "disabled_steps_wd_baru"
    MODE_NAME = "BOT WD XLM - MODE BARU (IMPORT PROFIL TANPA AUTH)"

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore
)
from wallet_phrase_helper import (
    get_available_wallet_files,
    load_wallet_phrases,
    get_phrase_by_index,
    copy_phrase_to_clipboard
)


# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Tambahkan path folder scrcpy / adb ke environment variables agar dikenali otomatis (hanya untuk PC)
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

current_step_info = "Menyiapkan bot..."

def log_step(text):
    global current_step_info
    current_step_info = text
    print(f"\n---> {text}")

MANUAL_MODE = "--manual" in sys.argv
REKAM_MODE  = "--rekam"  in sys.argv

def handle_pause(pause_reason="TOMBOL 'P' / CTRL+C DITEKAN", remaining_time=0):
    """
    Menangani status PAUSE pada bot dan menunggu shortcut Lanjut / Keluar:
    - Shortcut Lanjut: ENTER atau Ctrl+V
    - Shortcut Keluar: 'q' / 'Q'
    """
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

            # Shortcut Lanjut: ENTER (\r, \n) atau Ctrl+V (\x16)
            if ch in (b'\r', b'\n', b'\x16'):
                key_name = "Ctrl+V" if ch == b'\x16' else "ENTER"
                print(f"\n[>] Shortcut '{key_name}' terdeteksi! Melanjutkan proses dalam 2 detik...")
                time.sleep(1)
                print("GO!\n")
                return True
            # Shortcut Keluar: 'q' / 'Q'
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
    """Di mode manual: Enter / Spasi / Ctrl+V = lanjut instan, p / Ctrl+C = pause, q = keluar."""
    print(f"\n[STEP-BY-STEP] Selesai: {step_title}")
    sys.stdout.write("--> Tekan ENTER untuk lanjut (atau 'Q' berhenti): ")
    sys.stdout.flush()

    if platform.system() == "Windows" and sys.stdin.isatty():
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                handle_pause("CTRL+C DITEKAN")
                sys.stdout.write("\n--> Tekan ENTER untuk lanjut (atau 'Q' berhenti): ")
                sys.stdout.flush()
                continue

            if ch in (b'\r', b'\n', b' ', b'\x16'):
                key_label = "ENTER" if ch in (b'\r', b'\n', b' ') else "Ctrl+V"
                sys.stdout.write(f" [{key_label}]\n")
                sys.stdout.flush()
                return 'next'
            elif ch in (b'p', b'P'):
                handle_pause("TOMBOL 'P' DITEKAN")
                sys.stdout.write("\n--> Tekan ENTER untuk lanjut (atau 'Q' berhenti): ")
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
    """
    Menunggu keputusan user setelah 1 akun clone selesai:
    - Shortcut Lanjut: ENTER atau Ctrl+V
    - Shortcut Pause : 'p' / 'P' atau Ctrl+C
    - Shortcut Keluar: 'q' / 'Q'
    - Input angka    : Ketik nomor clone manual lalu Enter / Ctrl+V
    """
    print(f"--> Tekan ENTER atau CTRL+V untuk lanjut loop WD clone berikutnya (ke-{next_account_num})")
    sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): ")
    sys.stdout.flush()

    if platform.system() == "Windows" and sys.stdin.isatty():
        buf = []
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                handle_pause("CTRL+C DITEKAN")
                print(f"\n--> Tekan ENTER atau CTRL+V untuk lanjut loop WD clone berikutnya (ke-{next_account_num})")
                sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): {''.join(buf)}")
                sys.stdout.flush()
                continue

            # 1. LANJUT: ENTER (\r, \n) atau Ctrl+V (\x16)
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

            # 2. PAUSE: 'p' / 'P'
            elif ch in (b'p', b'P') and not buf:
                handle_pause("TOMBOL 'P' DITEKAN")
                print(f"\n--> Tekan ENTER atau CTRL+V untuk lanjut loop WD clone berikutnya (ke-{next_account_num})")
                sys.stdout.write(f"    (atau ketik nomor clone lain, atau 'Q' untuk kembali): ")
                sys.stdout.flush()

            # 3. KELUAR: 'q' / 'Q'
            elif ch in (b'q', b'Q') and not buf:
                sys.stdout.write("q\n")
                sys.stdout.flush()
                return 'q'

            # 4. BACKSPACE
            elif ch == b'\x08':
                if buf:
                    buf.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()

            # 5. INPUT ANGKA / KARAKTER
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

def prompt_number_with_arrows(prompt_label: str, default_val: int = 1, min_val: int = 0, max_val: int = 99999) -> int:
    """
    Input angka interaktif di console:
    - Panah Atas / Kanan : Tambah angka (+1)
    - Panah Bawah / Kiri : Kurangi angka (-1)
    - Ketik Angka (0-9)  : Masukkan angka manual
    - Backspace          : Hapus digit terakhir
    - Enter / Ctrl+V     : Konfirmasi angka
    """
    current_val = int(default_val)
    user_has_typed = False
    buffer_str = str(current_val)
    base_prompt = prompt_label.rstrip() + " "

    def redraw(val_str):
        line = f"{base_prompt}{val_str}"
        sys.stdout.write(f"\r{line}      \r{line}")
        sys.stdout.flush()

    redraw(buffer_str)

    if platform.system() == "Windows" and sys.stdin.isatty():
        import msvcrt
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                sys.stdout.write("\n")
                sys.stdout.flush()
                raise

            # Tombol panah di Windows
            if ch in (b'\x00', b'\xe0'):
                sc = msvcrt.getch()
                if sc in (b'H', b'M'):  # Panah Atas / Kanan -> Tambah (+1)
                    current_val = min(current_val + 1, max_val)
                    buffer_str = str(current_val)
                    user_has_typed = False
                    redraw(buffer_str)
                elif sc in (b'P', b'K'):  # Panah Bawah / Kiri -> Kurang (-1)
                    current_val = max(current_val - 1, min_val)
                    buffer_str = str(current_val)
                    user_has_typed = False
                    redraw(buffer_str)
                continue

            # Enter (\r, \n) atau Ctrl+V (\x16)
            if ch in (b'\r', b'\n', b'\x16'):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return int(buffer_str) if (buffer_str.isdigit() and int(buffer_str) >= min_val) else current_val

            # Backspace (\x08)
            if ch == b'\x08':
                if len(buffer_str) > 1:
                    buffer_str = buffer_str[:-1]
                else:
                    buffer_str = "0"
                current_val = int(buffer_str)
                user_has_typed = True
                redraw(buffer_str)
                continue

            try:
                char = ch.decode('latin1')
            except Exception:
                continue

            if char.isdigit():
                if not user_has_typed:
                    buffer_str = char
                    user_has_typed = True
                else:
                    if buffer_str == "0":
                        buffer_str = char
                    else:
                        buffer_str += char

                if len(buffer_str) > 5:
                    buffer_str = buffer_str[:5]

                val = int(buffer_str)
                if val > max_val:
                    val = max_val
                    buffer_str = str(val)
                current_val = val
                redraw(buffer_str)
            elif ch == b'\x03':  # Ctrl+C
                sys.stdout.write("\n")
                sys.stdout.flush()
                raise KeyboardInterrupt

    elif sys.stdin.isatty():
        # Fallback Linux / Termux ANSI input
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt
                if ch in ('\r', '\n', '\x16'):
                    break
                if ch == '\x1b':
                    seq = sys.stdin.read(2)
                    if seq in ('[A', '[C'):  # Up atau Right Arrow
                        current_val = min(current_val + 1, max_val)
                        buffer_str = str(current_val)
                        user_has_typed = False
                        redraw(buffer_str)
                    elif seq in ('[B', '[D'):  # Down atau Left Arrow
                        current_val = max(current_val - 1, min_val)
                        buffer_str = str(current_val)
                        user_has_typed = False
                        redraw(buffer_str)
                    continue
                if ch in ('\x7f', '\x08'):  # Backspace
                    if len(buffer_str) > 1:
                        buffer_str = buffer_str[:-1]
                    else:
                        buffer_str = "0"
                    current_val = int(buffer_str)
                    user_has_typed = True
                    redraw(buffer_str)
                    continue
                if ch.isdigit():
                    if not user_has_typed:
                        buffer_str = ch
                        user_has_typed = True
                    else:
                        if buffer_str == "0":
                            buffer_str = ch
                        else:
                            buffer_str += ch
                    if len(buffer_str) > 5:
                        buffer_str = buffer_str[:5]
                    val = int(buffer_str)
                    if val > max_val:
                        val = max_val
                        buffer_str = str(val)
                    current_val = val
                    redraw(buffer_str)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            sys.stdout.write("\n")
            sys.stdout.flush()
        return int(buffer_str) if (buffer_str.isdigit() and int(buffer_str) >= min_val) else current_val
    else:
        try:
            inp = input().strip()
            return int(inp) if inp.isdigit() else default_val
        except Exception:
            return default_val

def stoppable_sleep(jeda):
    """
    Tunggu selama 'jeda' detik.
    - Shortcut Pause : Tombol 'p' / 'P' atau 'Ctrl+C'
    - Shortcut Lanjut: Tombol ENTER atau 'Ctrl+V'
    - Shortcut Keluar: Tombol 'q' / 'Q'
    """
    end_time = time.time() + jeda

    while time.time() < end_time:
        paused = False
        pause_reason = ""

        if platform.system() == "Windows" and sys.stdin.isatty():
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # Shortcut Pause: 'p' / 'P' atau Ctrl+C (\x03)
                    if key in (b'p', b'P', b'\x03'):
                        paused = True
                        pause_reason = "TOMBOL 'P' DITEKAN" if key in (b'p', b'P') else "CTRL+C DITEKAN"
                    # Shortcut Keluar: 'q' / 'Q'
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
    print(f"Tapping at ({x}, {y})")
    adb_command(f"shell input tap {x} {y}")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)

def swipe(x1, y1, x2, y2, duration=500, jeda=1.0):
    """Simulasi geser (swipe) pada layar."""
    print(f"Swiping from ({x1}, {y1}) to ({x2}, {y2})")
    adb_command(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)

def input_text(text, jeda=1.0):
    """Input teks ke dalam kolom yang sedang aktif."""
    print(f"Typing text: {text}")
    text = str(text).replace(' ', '%s')
    adb_command(f"shell input text '{text}'")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)

def paste_clipboard(jeda=1.0):
    """Mensimulasikan aksi Paste (Tempel) dari clipboard bawaan Android."""
    print(f"Pasting from clipboard")
    adb_command("shell input keyevent 279")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)

def press_back(jeda=1.0):
    """Mensimulasikan tombol Back sistem."""
    print(f"Pressing BACK")
    adb_command("shell input keyevent 4")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)
    
def open_recent_apps(jeda=2.0):
    """Membuka layar Recent Apps."""
    print(f"Opening Recent Apps")
    adb_command("shell input keyevent 187")
    if not (MANUAL_MODE or REKAM_MODE):
        stoppable_sleep(jeda)

def tap_dynamic_pin(pin_str, keypad_coords, final_jeda=5.0):
    """Melakukan ketikan PIN secara dinamis menggunakan mapping koordinat."""
    print(f"Memasukkan PIN dinamis via kordinat sentuh...")
    is_fast = MANUAL_MODE or REKAM_MODE
    digit_jeda = 0.08 if is_fast else 0.35
    for i, digit in enumerate(pin_str):
        if digit in keypad_coords:
            coord = keypad_coords[digit]
            is_last = (i == len(pin_str) - 1)
            jeda_to_use = (0.2 if is_fast else final_jeda) if is_last else digit_jeda
            print(f"  Digit [{digit}] -> ({coord['x']}, {coord['y']})")
            adb_command(f"shell input tap {coord['x']} {coord['y']}")
            stoppable_sleep(jeda_to_use)
        else:
            print(f"Peringatan: Koordinat untuk angka {digit} tidak ditemukan!")

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Gagal memuat {CONFIG_FILE}: {e}")
        sys.exit(1)

def save_config(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Gagal menyimpan {CONFIG_FILE}: {e}")


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

def update_sleep_in_kordinat(step_id, new_sleep_value, filepath=None):
    """
    Menulis ulang nilai sleep terakhir sebuah step di file koordinat aktif
    dengan nilai delay hasil rekaman user (dibulatkan 1 desimal).
    Jika step tidak punya 'sleep' sama sekali, tambahkan di akhir block step.
    """
    if filepath is None:
        filepath = KORDINAT_FILE
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
    cmd = cmd.replace("{PHRASE}", str(context.get("PHRASE", "")))

    parts = cmd.split()
    if not parts:
        return

    cmd_lower = parts[0].lower()
    full_lower = cmd.lower().strip()

    # Perintah phrase clipboard & input
    if full_lower in ("input phrase_copy", "phrase_copy"):
        p_val = context.get("PHRASE", "")
        if p_val:
            copy_phrase_to_clipboard(p_val)
            print(f"[*] [CLIPBOARD PC] 12 Kata Frasa Akun #{context.get('ACCOUNT_NUM', '')} disalin ke clipboard:")
            print(f"    -> {p_val}")
        else:
            print("[!] Peringatan: Frasa akun kosong / tidak ditemukan.")
        return

    if full_lower in ("input phrase_paste", "phrase_paste"):
        print("[*] Mencoba Tempel Frasa (Paste) via Keyevent 279...")
        adb_command("shell input keyevent 279")
        return

    if full_lower in ("input phrase_type", "phrase_type"):
        p_val = context.get("PHRASE", "")
        if p_val:
            print(f"[*] Memasukkan 12 kata frasa langsung ke HP via ADB:")
            print(f"    -> {p_val}")
            escaped = p_val.replace(" ", "%s")
            adb_command(f"shell input text '{escaped}'")
        else:
            print("[!] Peringatan: Frasa akun kosong / tidak ditemukan.")
        return

    # Perintah jeda waktu: "sleep 1.5"
    if cmd_lower == "sleep":
        if MANUAL_MODE or REKAM_MODE:
            return  # Bypass sleep di mode manual & rekam delay agar instan & bisa spam Enter!
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
    DISABLED_STEPS = config.get(CONFIG_DISABLED_KEY, config.get("disabled_steps", []))

    steps = parse_kordinat_file(KORDINAT_FILE)
    active_steps = [s for s in steps if is_step_enabled(s)]

    print(f"\n[*] {MODE_NAME}")
    print(f"[*] Berhasil memuat {len(steps)} langkah ({len(active_steps)} aktif) dari {os.path.basename(KORDINAT_FILE)}")
    print(f"""
=========================================================
               MODE REKAM DELAY AKTIF
=========================================================
  Cara kerja:
  1. Bot jalankan semua klik/swipe/action per step.
  2. Stopwatch dimulai segera setelah action selesai.
  3. Tekan ENTER saat layar HP sudah siap ke langkah
     berikutnya. Waktu akan otomatis disimpan ke
     {os.path.basename(KORDINAT_FILE)} sebagai delay baru.
  4. Ketik 'S' + ENTER untuk SKIP step (delay tidak
     diubah untuk step tersebut).
  5. Ketik 'Q' + ENTER untuk BERHENTI merekam.

  Rekaman menggunakan 1 akun frasa yang Anda tentukan.
  Setelah rekam, jalankan WD Otomatis (Menu 1).
=========================================================
""")
    active_file = config.get("active_wallet_file")
    all_wallet_files = get_available_wallet_files()
    if not active_file and all_wallet_files:
        active_file = all_wallet_files[0]
        config["active_wallet_file"] = active_file
        save_config(config)

    default_idx = config.get("start_index", 1)
    print(f"[*] File Wallet Digunakan  : {active_file}")
    target_idx = prompt_number_with_arrows(
        "[?] Gunakan frasa wallet nomor urut berapa untuk rekam? [Panah Atas/Bawah | Ketik]:",
        default_val=default_idx,
        min_val=1
    )

    p_data = get_phrase_by_index(target_idx, active_file)
    phrase_val = p_data["phrase"] if p_data else ""
    if phrase_val:
        copy_phrase_to_clipboard(phrase_val)

    raw_no_info = f" (No File: #{p_data.get('raw_num')})" if (p_data and p_data.get('raw_num')) else ""
    ref_info = f" | Ref: {p_data.get('ref_code')}" if (p_data and p_data.get("ref_code")) else ""

    print(f"\n[*] Akun Dipilih Untuk Rekam : Akun #{target_idx}{raw_no_info}{ref_info}")
    print(f"[*] 12 Kata Frasa (Lengkap):")
    print(f"    -> {phrase_val if phrase_val else '(TIDAK DITEMUKAN / KOSONG)'}")
    print(f"[*] Frasa otomatis disalin ke clipboard PC.")

    input("\n--> Siapkan HP Anda, lalu tekan ENTER untuk mulai rekam...")

    context = {
        "ALAMAT_WD": ALAMAT_WD,
        "ACCOUNT_NUM": target_idx,
        "PIN": PIN,
        "KEYPAD": KEYPAD,
        "PHRASE": phrase_val,
        "WALLET_FILE": active_file
    }

    recorded = {}

    for step in active_steps:
        step_id = step["id"]
        log_step(f"# {step['full_title']}")

        # Jalankan semua action (SKIP sleep agar tidak ada jeda otomatis)
        for cmd in step["commands"]:
            if not is_action_cmd(cmd):
                continue
            execute_step_command(cmd, context)

        # Mulai stopwatch timer tepat setelah perintah sentuh dikirim ke HP
        t_start = time.time()

        prompt_msg = f"  --> [REKAM DELAY] Tekan ENTER saat layar HP siap (S=Skip | Q=Berhenti): "
        sys.stdout.write(prompt_msg)
        sys.stdout.flush()

        user_key = 'enter'
        if platform.system() == "Windows" and sys.stdin.isatty():
            while True:
                try:
                    ch = msvcrt.getch()
                except KeyboardInterrupt:
                    user_key = 'q'
                    break
                if ch in (b'\r', b'\n', b' '):
                    sys.stdout.write(" [ENTER]\n")
                    sys.stdout.flush()
                    user_key = 'enter'
                    break
                elif ch in (b's', b'S'):
                    sys.stdout.write(" [SKIP]\n")
                    sys.stdout.flush()
                    user_key = 's'
                    break
                elif ch in (b'q', b'Q'):
                    sys.stdout.write(" [STOP]\n")
                    sys.stdout.flush()
                    user_key = 'q'
                    break
        else:
            try:
                line = sys.stdin.readline().strip().lower()
                if line in ('s', 'skip'):
                    user_key = 's'
                elif line in ('q', 'quit', 'exit'):
                    user_key = 'q'
            except KeyboardInterrupt:
                user_key = 'q'

        elapsed = round(time.time() - t_start, 1)

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
        print(f"  [V]  Delay step {step_id} direkam: {elapsed}s  -> disimpan ke {os.path.basename(KORDINAT_FILE)}")

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
    # Konfigurasi Akun & Kredensial
    ALAMAT_WD  = config.get("alamat_wd", "")
    PIN        = config.get("pin", "080808")
    KEYPAD     = config.get("keypad_coords", {})
    DISABLED_STEPS = config.get(CONFIG_DISABLED_KEY, config.get("disabled_steps", []))

    # Nomor Urut Terakhir / Awal untuk Penamaan di Google Authenticator (Default: 0)
    START_INDEX = config.get("start_index", 0)

    print(f"\n[*] {MODE_NAME}")
    print(f"[*] File Koordinat: {os.path.basename(KORDINAT_FILE)}")
    print(f"[?] Bot berjalan dalam mode loop akun.")
    print(f"[?] Shortcut Lanjut: ENTER atau Ctrl+V | Pause: 'P' atau Ctrl+C | Keluar: 'Q'")
    START_INDEX = prompt_number_with_arrows(
        "[?] Mulai dari clone nomor berapa? [Panah Atas/Bawah | Ketik]:",
        default_val=START_INDEX,
        min_val=0
    )

    # Simpan nomor awal yang dipilih jika berbeda
    if config.get("start_index") != START_INDEX:
        config["start_index"] = START_INDEX
        save_config(config)

    # Baca file koordinat
    steps = parse_kordinat_file(KORDINAT_FILE)
    print(f"[*] Berhasil memuat {len(steps)} langkah automasi dari {os.path.basename(KORDINAT_FILE)}")

    # Sinkronisasi status OFF dari kordinat file ke config.json jika ada perbedaan
    file_disabled = [s['id'] for s in steps if s['is_off']]
    if sorted([str(x) for x in DISABLED_STEPS]) != sorted([str(x) for x in file_disabled]):
        DISABLED_STEPS = file_disabled
        config[CONFIG_DISABLED_KEY] = DISABLED_STEPS
        save_config(config)

    if DISABLED_STEPS:
        print(f"[!] Step yang di-SKIP: {DISABLED_STEPS}")

    current_account_num = START_INDEX

    active_file = config.get("active_wallet_file")
    all_wallet_files = get_available_wallet_files()
    if not active_file and all_wallet_files:
        active_file = all_wallet_files[0]
        config["active_wallet_file"] = active_file
        save_config(config)

    try:
        while True:
            p_data = get_phrase_by_index(current_account_num, active_file)
            phrase_val = p_data["phrase"] if p_data else ""
            if phrase_val:
                copy_phrase_to_clipboard(phrase_val)

            raw_no_info = f" (No File: #{p_data.get('raw_num')})" if (p_data and p_data.get('raw_num')) else ""
            ref_info = f" | Ref: {p_data.get('ref_code')}" if (p_data and p_data.get("ref_code")) else ""

            print(f"\n=========================================================")
            print(f"           MEMPROSES AKUN CLONE KE-{current_account_num}{raw_no_info}          ")
            print(f"[*] File Wallet        : {active_file}")
            print(f"[*] 12 Kata Frasa (Lengkap):")
            print(f"    -> {phrase_val if phrase_val else '(TIDAK DITEMUKAN / HABIS)'}{ref_info}")
            print(f"=========================================================\n")

            context = {
                "ALAMAT_WD": ALAMAT_WD,
                "ACCOUNT_NUM": current_account_num,
                "PIN": PIN,
                "KEYPAD": KEYPAD,
                "PHRASE": phrase_val,
                "WALLET_FILE": active_file
            }

            user_aborted = False
            for step in steps:
                step_id = step["id"]
                if not is_step_enabled(step):
                    print(f"[SKIP] Step {step_id}: {step['name']}")
                    continue

                log_step(f"# {step['full_title']}")
                for cmd in step["commands"]:
                    execute_step_command(cmd, context)

                if MANUAL_MODE:
                    step_action = prompt_manual_step(step['full_title'])
                    if step_action == 'q':
                        print("\n[X] Eksekusi dihentikan oleh pengguna.")
                        user_aborted = True
                        break

            if user_aborted:
                config["start_index"] = current_account_num
                save_config(config)
                return

            # Akun saat ini berhasil selesai diproses!
            next_account_num = current_account_num + 1

            # Ingat urutan terakhir: simpan nomor clone berikutnya ke config.json
            config["start_index"] = next_account_num
            save_config(config)

            print(f"\n=========================================================")
            print(f"[V] AKUN CLONE KE-{current_account_num} BERHASIL SELESAI DIPROSES!")
            print(f"[*] Urutan berikutnya tersimpan di config: Clone ke-{next_account_num}")
            print(f"=========================================================")
            user_choice = prompt_next_clone(next_account_num)

            if isinstance(user_choice, str) and user_choice.lower() in ('q', 'quit', 'exit', '0'):
                print(f"\n[*] Selesai. Urutan terakhir tersimpan untuk eksekusi berikutnya: Clone ke-{next_account_num}.")
                break
            elif isinstance(user_choice, int):
                current_account_num = user_choice
                config["start_index"] = current_account_num
                save_config(config)
            else:
                current_account_num = next_account_num

    except KeyboardInterrupt:
        handle_pause("CTRL+C DITEKAN")
        config["start_index"] = current_account_num
        save_config(config)
        return

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

