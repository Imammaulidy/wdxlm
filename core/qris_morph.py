"""
BOT ADB TERMINAL STANDALONE - BITGET WALLET QRIS MORPH
========================================================
Modul otomasi Bitget Wallet QRIS Morph L2:
- Mode interaktif INSTAN 1-touch (langsung jalan tanpa harus tekan ENTER)
- Full Auto: Reset Clone -> Gen QRIS -> Tebar USDC Morph L2 -> Bayar PIN -> Claim Cashback Reward
- Mode Manual Step-by-Step
- Mode Rekam Delay HP
- Auto Reset Cache, Google Advertising ID (ID Iklan), Mode Pesawat 3 detik
- Dukungan scrcpy mirror screen (-S -w)
- Generator GoBiz QRIS Dinamis & Auto-Push ke HP
- Pengelolaan ON/OFF step koordinat macro (kordinat_qris_morph.txt)
"""

import os
import sys
import json
import time
import shutil
import subprocess
import re
from typing import Optional, Dict, Any, List

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    register_auto_restore,
    read_current_screen,
    get_cached_screen
)
from adb_controller import ADBController, CLONE_APPS
from gobiz_qris import (
    GoBizQRISGenerator,
    fetch_gobiz_merchant_info,
    extract_token_from_input,
    get_gobiz_accounts,
    get_active_gobiz_account,
    rotate_gobiz_shift
)
from morph_wallet import MorphWallet

CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
CONFIG_EXAMPLE = os.path.join(CORE_DIR, 'config.example.json')
KORDINAT_FILE = os.path.join(CORE_DIR, 'kordinat_qris_morph.txt')
DISABLED_CONFIG_KEY = "disabled_steps_qris_morph"
LAST_TUYUL_FILE = os.path.join(CORE_DIR, '.last_tuyul.txt')
TEMP_QR_PATH = os.path.join(CORE_DIR, 'qris_pay.png')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif os.path.exists(CONFIG_EXAMPLE):
        with open(CONFIG_EXAMPLE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(cfg: Dict[str, Any]):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)

def get_last_tuyul_address() -> str:
    if os.path.exists(LAST_TUYUL_FILE):
        try:
            with open(LAST_TUYUL_FILE, 'r', encoding='utf-8') as f:
                addr = f.read().strip()
                if addr.startswith("0x") and len(addr) == 42:
                    return addr
        except Exception:
            pass
    return ""

def save_last_tuyul_address(address: str):
    try:
        with open(LAST_TUYUL_FILE, 'w', encoding='utf-8') as f:
            f.write(address.strip())
    except Exception:
        pass

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

def wait_any_key(prompt: str = "\n Tekan sembarang tombol untuk kembali..."):
    """Menunggu sembarang tombol ditekan secara instan."""
    print(prompt, end="", flush=True)
    if os.name == 'nt':
        import msvcrt
        ch = msvcrt.getch()
        if ch == b'\x03':
            raise KeyboardInterrupt
        print()
    else:
        input()

def parse_step_header(line: str):
    """Mem-parsing baris judul step dari kordinat_qris_morph.txt."""
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
        step_id = raw_id
        step_name = id_m.group(2).strip() or inner
    else:
        step_id = inner
        step_name = inner

    if suffix and suffix.upper() != "OFF":
        step_name = f"{step_name} ({suffix})"

    return {
        "id": str(step_id),
        "name": step_name,
        "full_title": inner,
        "is_off": is_off,
        "suffix": suffix
    }

def get_kordinat_steps_from_file(filepath: str = KORDINAT_FILE) -> List[Dict[str, Any]]:
    """Membaca daftar header langkah dari file kordinat_qris_morph.txt."""
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

def sync_kordinat_and_config(filepath: str = KORDINAT_FILE):
    """Menyelaraskan status OFF antara kordinat_qris_morph.txt dan config.json['disabled_steps_qris_morph']."""
    if not os.path.exists(CONFIG_FILE):
        return
    config = load_config()
    changed = False

    if os.path.exists(filepath):
        steps = get_kordinat_steps_from_file(filepath)
        file_disabled = [str(s['id']) for s in steps if s['is_off']]
        current_disabled = [str(x) for x in config.get(DISABLED_CONFIG_KEY, [])]
        if sorted(current_disabled) != sorted(file_disabled):
            config[DISABLED_CONFIG_KEY] = file_disabled
            changed = True

    if changed:
        save_config(config)

def update_kordinat_txt_step_file(filepath: str, target_step_id: str, set_off: bool):
    """Memperbarui status OFF untuk step tertentu di file koordinat."""
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
        if str(raw_id) != str(target_step_id):
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

def update_all_kordinat_txt_steps_file(filepath: str, set_off: bool):
    """Mengaktifkan atau menonaktifkan semua step di file koordinat."""
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
            new_line = f"{new_bracket} {clean_after} OFF\n" if clean_after else f"{new_bracket} OFF\n"
        else:
            new_line = f"{new_bracket} {clean_after}\n" if clean_after else f"{new_bracket}\n"
        new_lines.append(new_line)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

def execute_toggle_steps_logic(target_file: str = KORDINAT_FILE, config_key: str = DISABLED_CONFIG_KEY):
    """Menu antarmuka interaktif ON/OFF step koordinat."""
    while True:
        sync_kordinat_and_config(target_file)
        config = load_config()
        disabled = config.get(config_key, [])
        disabled_str = [str(x) for x in disabled]
        steps = get_kordinat_steps_from_file(target_file)
        clear_screen()
        file_name = os.path.basename(target_file)
        print("="*65)
        print(f"     PENGATURAN ON/OFF STEP KOORDINAT ({file_name})     ")
        print("="*65)
        print(f"  {'NO':>4}  {'STEP':<5}  {'STATUS':<6}  DESKRIPSI")
        print("-" * 65)
        for idx, step in enumerate(steps, start=1):
            s_id = str(step['id'])
            is_off = step['is_off'] or s_id in disabled_str
            status = "[ ON ]" if not is_off else "[OFF ]"
            print(f"  {idx:>4}. Step {s_id:<4} {status}  {step['name']}")
        print("-" * 65)
        print("  A  = AKTIFKAN SEMUA STEP (Hapus penanda OFF di file)")
        print("  D  = DISABLE SEMUA STEP (Pasang penanda OFF di file)")
        print("  0  = Kembali ke Menu Sebelumnya")
        print("="*65)
        pil = input(" Masukkan nomor step untuk toggle (atau A/D/0): ").strip().upper()

        if pil == '0':
            break
        elif pil == 'A':
            config[config_key] = []
            save_config(config)
            update_all_kordinat_txt_steps_file(target_file, set_off=False)
            print(f"\n[V] Semua step DIAKTIFKAN di {file_name}!")
            time.sleep(1)
        elif pil == 'D':
            config[config_key] = [str(s['id']) for s in steps]
            save_config(config)
            update_all_kordinat_txt_steps_file(target_file, set_off=True)
            print(f"\n[!] Semua step DINONAKTIFKAN di {file_name}!")
            time.sleep(1)
        elif pil.replace('.', '', 1).isdigit():
            target_step = None
            if pil.isdigit():
                idx_pil = int(pil) - 1
                if 0 <= idx_pil < len(steps):
                    target_step = steps[idx_pil]
            if not target_step:
                for s in steps:
                    if str(s['id']) == pil:
                        target_step = s
                        break

            if target_step:
                s_id = str(target_step['id'])
                is_currently_off = target_step['is_off'] or s_id in disabled_str
                new_off_state = not is_currently_off

                if new_off_state:
                    if s_id not in disabled_str:
                        disabled_str.append(s_id)
                    update_kordinat_txt_step_file(target_file, s_id, set_off=True)
                    print(f"\n[!] Step {s_id} [{target_step['name']}] -> OFF")
                else:
                    disabled_str = [x for x in disabled_str if x != s_id]
                    update_kordinat_txt_step_file(target_file, s_id, set_off=False)
                    print(f"\n[V] Step {s_id} [{target_step['name']}] -> ON")

                config[config_key] = disabled_str
                save_config(config)
                time.sleep(0.6)
            else:
                print("\n[!] Nomor step tidak ditemukan!")
                time.sleep(1)
        else:
            print("\n[!] Pilihan tidak dikenali!")
            time.sleep(1)

def update_sleep_in_kordinat(step_id: str, new_sleep_value: float, filepath: str = KORDINAT_FILE):
    """Menulis ulang nilai sleep terakhir sebuah step di kordinat_qris_morph.txt."""
    if not os.path.exists(filepath):
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_val = f"{round(float(new_sleep_value), 1)}"

    block_start = None
    block_end = None
    in_target = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        header = parse_step_header(stripped)
        if header is not None:
            if in_target:
                block_end = i
                break
            if str(header['id']) == str(step_id):
                block_start = i
                in_target = True
        elif in_target and (stripped.startswith('---') or stripped == ''):
            block_end = i
            break

    if block_start is None:
        return

    if block_end is None:
        block_end = len(lines)

    last_sleep_idx = None
    for i in range(block_start, block_end):
        parts = lines[i].strip().split()
        if parts and parts[0].lower() == 'sleep':
            last_sleep_idx = i

    if last_sleep_idx is not None:
        indent = lines[last_sleep_idx][:len(lines[last_sleep_idx]) - len(lines[last_sleep_idx].lstrip())]
        lines[last_sleep_idx] = f"{indent}sleep {new_val}\n"
    else:
        lines.insert(block_end, f"sleep {new_val}\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def prompt_manual_step(step_title: str) -> str:
    """Di mode manual: Enter / Spasi = lanjut, Q = keluar."""
    print(f"\n[STEP-BY-STEP] Selesai: {step_title}")
    sys.stdout.write("--> Tekan ENTER untuk lanjut ke langkah berikutnya (atau 'Q' untuk berhenti): ")
    sys.stdout.flush()
    if os.name == 'nt':
        import msvcrt
        while True:
            try:
                ch = msvcrt.getch()
            except KeyboardInterrupt:
                return 'q'
            if ch in (b'\r', b'\n', b'\x16', b' '):
                print(" [ENTER]")
                return 'next'
            elif ch in (b'q', b'Q'):
                print(" Q")
                return 'q'
    else:
        try:
            line = sys.stdin.readline().strip().lower()
            if line in ('q', 'quit', 'exit'):
                return 'q'
            return 'next'
        except KeyboardInterrupt:
            return 'q'

def parse_macro_steps(filepath: str = KORDINAT_FILE) -> List[Dict[str, Any]]:
    """Membaca langkah-langkah macro dari kordinat_qris_morph.txt."""
    if not os.path.exists(filepath):
        return []

    cfg = load_config()
    disabled_str = [str(x) for x in cfg.get(DISABLED_CONFIG_KEY, [])]

    steps = []
    current_step = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            raw_line = line.strip()
            if not raw_line or raw_line.startswith("#") or raw_line.startswith("---"):
                continue

            header = parse_step_header(raw_line)
            if header:
                if current_step:
                    steps.append(current_step)
                sid = str(header["id"])
                is_off = header["is_off"] or sid in disabled_str
                current_step = {
                    "id": sid,
                    "name": header["name"],
                    "is_off": is_off,
                    "commands": []
                }
                continue

            if current_step:
                current_step["commands"].append(raw_line)

    if current_step:
        steps.append(current_step)

    return steps

class BotRunner:
    """Eksekutor Alur Bot Bitget Terminal Standalone QRIS Morph."""

    def __init__(self):
        self.config = load_config()
        self.adb = ADBController()
        self.qris_gen = GoBizQRISGenerator(self.config)
        self.wallet = MorphWallet(
            private_key=self.config.get("wallet_tebar", {}).get("private_key"),
            custom_rpc=self.config.get("morph", {}).get("rpc_url")
        )
        self.stopped = False
        self.is_manual = False

    def check_keyboard_interrupt(self) -> str:
        """Non-blocking keyboard checker (stop / pause / continue)."""
        if os.name == 'nt':
            import msvcrt
            while msvcrt.kbhit():
                try:
                    ch = msvcrt.getch()
                    if ch in (b'\x03', b'q', b'Q', b'\x1b'):
                        return "stop"
                    elif ch in (b'p', b'P', b' '):
                        return "pause"
                except Exception:
                    pass
        return "continue"

    def handle_pause(self) -> bool:
        """Menangani jeda (PAUSE) pada bot dan menunggu shortcut Lanjut / Keluar."""
        print("\n\n" + "="*70)
        print(" [!!!] ALUR BOT DIPAUSE (JEDA SEMENTARA) [!!!]")
        print("======================================================================")
        print(" Silakan cek atau perbaiki layar HP Anda.")
        print(" --> Tekan ENTER atau SPASI untuk MELANJUTKAN")
        print(" --> Tekan 'Q' atau ESC untuk STOP & KEMBALI KE MENU")
        print("======================================================================")

        if os.name == 'nt':
            import msvcrt
            while True:
                try:
                    ch = msvcrt.getch()
                except KeyboardInterrupt:
                    print("\n[!] Dihentikan oleh user (Ctrl+C).")
                    self.stopped = True
                    return False

                if ch in (b'\r', b'\n', b'\x16', b' '):
                    print("\n[>] Melanjutkan alur bot dalam 1 detik...")
                    time.sleep(1.0)
                    return True
                elif ch in (b'q', b'Q', b'\x1b'):
                    print("\n[!] Alur dibatalkan oleh user ('Q'). Kembali ke menu...")
                    self.stopped = True
                    return False
        else:
            try:
                line = input("\nTekan ENTER untuk lanjut (Q untuk stop): ").strip().lower()
                if line in ('q', 'quit', 'exit'):
                    self.stopped = True
                    return False
                return True
            except KeyboardInterrupt:
                self.stopped = True
                return False

    def smart_sleep(self, seconds: float, force: bool = False) -> bool:
        """Sleep yang reaktif terhadap keyboard interrupt (Stop / Pause). Di mode manual, otomatis di-bypass agar instan."""
        if self.stopped:
            return False

        if seconds <= 0 or (self.is_manual and not force):
            return True

        end_time = time.time() + seconds
        while time.time() < end_time:
            if self.stopped:
                return False
            action = self.check_keyboard_interrupt()
            if action == "stop":
                print("\n[!] Alur dihentikan oleh pengguna (STOP). Kembali ke menu utama...", flush=True)
                self.stopped = True
                return False
            elif action == "pause":
                if not self.handle_pause():
                    return False
            time.sleep(0.05)

        return not self.stopped

    def is_stopped(self) -> bool:
        """Callback checker untuk ADB controller dan alur."""
        if self.stopped:
            return True
        act = self.check_keyboard_interrupt()
        if act == "stop":
            print("\n[!] Alur dihentikan oleh pengguna (STOP).", flush=True)
            self.stopped = True
            return True
        elif act == "pause":
            if not self.handle_pause():
                return True
        return False

    def execute_macro_step(self, step_id: str, skip_sleep: bool = False, force: bool = False) -> bool:
        """Menjalankan single macro step berdasarkan ID."""
        if self.stopped:
            return False

        act = self.check_keyboard_interrupt()
        if act == "stop":
            print("\n[!] Alur dihentikan oleh pengguna (STOP). Kembali ke menu utama...", flush=True)
            self.stopped = True
            return False
        elif act == "pause":
            if not self.handle_pause():
                return False

        steps = parse_macro_steps()
        target = None
        for s in steps:
            if str(s["id"]) == str(step_id):
                target = s
                break

        if not target:
            print(f"[!] Step {step_id} tidak ditemukan di {os.path.basename(KORDINAT_FILE)}.")
            return False

        if target["is_off"] and not force:
            print(f"[*] Step [{target['id']}. {target['name']}] diatur OFF (dilewati).")
            return True

        print(f"\n[>] Menjalankan Step [{target['id']}. {target['name']}]...")
        for cmd in target["commands"]:
            if self.stopped:
                return False
            ok = self._run_single_command(cmd, skip_sleep=skip_sleep)
            if not ok or self.stopped:
                return False
        return True

    def is_step_enabled(self, step_id: str) -> bool:
        """Mengecek apakah step tertentu berstatus aktif (ON)."""
        cfg = load_config()
        disabled_str = [str(x) for x in cfg.get(DISABLED_CONFIG_KEY, [])]
        if str(step_id) in disabled_str:
            return False
        steps = parse_macro_steps()
        for s in steps:
            if str(s["id"]) == str(step_id):
                return not s.get("is_off", False)
        return True

    def run_step_flow(self, step_id: str, label: str, is_manual: bool = False) -> bool:
        """Menjalankan step dalam alur bot, dengan otomatis skip jika OFF dan prompt jika mode manual."""
        if not self.is_step_enabled(step_id):
            print(f"[*] Step {step_id} ({label}) diatur OFF (dilewati).")
            return True
        if not self.execute_macro_step(step_id, skip_sleep=is_manual):
            return False
        if is_manual and prompt_manual_step(f"Step {step_id} ({label})") == 'q':
            self.stopped = True
            return False
        return True

    def _run_single_command(self, cmd_line: str, skip_sleep: bool = False) -> bool:
        if self.stopped:
            return False

        act = self.check_keyboard_interrupt()
        if act == "stop":
            print("\n[!] Alur dihentikan oleh pengguna (STOP).", flush=True)
            self.stopped = True
            return False
        elif act == "pause":
            if not self.handle_pause():
                return False

        parts = cmd_line.split()
        if not parts:
            return True

        action = parts[0].lower()

        if action == "sleep" and len(parts) >= 2:
            if skip_sleep:
                return True
            try:
                sec = float(parts[1])
                return self.smart_sleep(sec)
            except ValueError:
                return True

        elif action == "input" and len(parts) >= 2:
            sub = parts[1].lower()
            if sub == "tap" and len(parts) >= 4:
                x = int(parts[2])
                y = int(parts[3])
                self.adb.tap(x, y, delay_after=0.2)
            elif sub == "swipe" and len(parts) >= 6:
                x1 = int(parts[2])
                y1 = int(parts[3])
                x2 = int(parts[4])
                y2 = int(parts[5])
                dur = int(parts[6]) if len(parts) >= 7 else 300
                self.adb.swipe(x1, y1, x2, y2, duration_ms=dur, delay_after=0.2)
            elif sub == "keyevent" and len(parts) >= 3:
                key_code = parts[2]
                self.adb.keyevent(key_code, delay_after=0.2)
            elif sub == "text" and len(parts) >= 3:
                txt = " ".join(parts[2:])
                self.adb.text_input(txt, delay_after=0.2)

        elif action == "pin":
            pin_code = parts[1] if len(parts) >= 2 else self.config.get("pin", "080808")
            if pin_code == "{PIN}":
                pin_code = self.config.get("pin", "080808")
            coords = self.config.get("keypad_coords_morph") or self.config.get("keypad_coords")
            self.adb.type_pin(pin_code, keypad_coords=coords, delay_step=0.3)

        else:
            # Perintah umum ADB shell (am, pm, cmd, monkey, dll)
            self.adb.run(f"shell {cmd_line}")

        return not self.stopped

    def run_full_auto(self) -> bool:
        """Menjalankan alur penuh secara Full Auto."""
        return self._execute_flow(is_manual=False)

    def run_manual_mode(self) -> bool:
        """Menjalankan alur secara Step-by-Step Manual."""
        return self._execute_flow(is_manual=True)

    def _execute_flow(self, is_manual: bool = False) -> bool:
        self.stopped = False
        self.is_manual = is_manual
        self.config = load_config()

        mode_label = "MODE STEP-BY-STEP MANUAL" if is_manual else "MODE FULL AUTO"
        clone_key = self.config.get("clone_app", "dual_space")
        clone_info = CLONE_APPS.get(clone_key, CLONE_APPS["dual_space"])
        current_nominal = int(self.config.get("default_qris_nominal", 18501))

        clear_screen()
        print("="*70)
        print(f"      MEMULAI {mode_label}")
        print(f"      Mode Clone Aktif : {clone_info['name']} ({clone_info['package']})")
        print(f"      Nominal QRIS     : Rp {current_nominal:,}".replace(",", "."))
        print("-"*70)
        print("  [KONTROL KEYBOARD AKTIF]")
        print("  * Tekan 'P' / SPASI : PAUSE (Jeda Alur)")
        print("  * Tekan 'Q' / ESC   : STOP (Hentikan Bot & Kembali ke Menu)")
        print("="*70)

        # 1. Pastikan Device Terhubung
        if not self.adb.check_connection():
            print("[X] ERROR: Tidak ada perangkat HP Android terdeteksi via ADB!")
            return False

        if self.stopped:
            return False

        # 2. Rekam & Terapkan Resolusi Standar Bot (1080x2400 @ 352 DPI)
        register_auto_restore()
        ok_scr, scr_msg = record_and_apply_bot_screen()
        if not ok_scr:
            print(f"[!] Peringatan Layar: {scr_msg}")

        if self.stopped:
            return False

        # 3. Reset Atomik Clone: Paksa Berhenti & Bersihkan Cache
        print("\n" + "="*60)
        print(f" MEMULAI RESET ATOMIK CLONE: {clone_info['name']}")
        print("="*60)
        if not self.adb.force_stop_and_clear_cache(clone_key, stop_checker=self.is_stopped):
            return False

        # Reset Google Advertising ID via Step Macro (0.1 s/d 0.8)
        print("\n[*] Menjalankan Reset Google Advertising ID (Delete -> Get New -> Reset)...")
        gaid_steps = [
            ("0.1", "Buka Pengaturan Iklan Google"),
            ("0.2", "Ketuk Delete Advertising ID"),
            ("0.3", "Ketuk Tombol Hijau Delete Advertising ID"),
            ("0.4", "Ketuk Get New Advertising ID"),
            ("0.5", "Ketuk Confirm Dialog Get New ID"),
            ("0.6", "Ketuk Reset Advertising ID"),
            ("0.7", "Ketuk Confirm Dialog Reset ID"),
            ("0.8", "Tutup Pengaturan Iklan & Kembali")
        ]
        for sid, slbl in gaid_steps:
            if not self.run_step_flow(sid, slbl, is_manual):
                return False

        # Mode Pesawat (Reset IP Jaringan)
        airplane_sec = self.config.get("airplane_seconds", 3)
        if not self.adb.toggle_airplane_mode(airplane_sec, stop_checker=self.is_stopped):
            return False

        # Buka kembali aplikasi Clone
        if not self.adb.launch_clone_app(clone_key, stop_checker=self.is_stopped):
            return False
        print("="*60 + "\n")

        # 4. Tunggu User Masuk ke Bitget Wallet di dalam Clone
        print("\n" + "-"*70)
        print(" [ACTION] SILAKAN KLIK & BUKA BITGET WALLET DI DALAM CLONE HP")
        print(" Buka slot dompet Bitget yang sedang digarap sampai di halaman beranda.")
        print(" [KONTROL] Tekan sembarang tombol jika sudah di beranda Bitget")
        print("           (Atau tekan 'Q' untuk STOP & Kembali ke Menu)")
        print("-"*70)

        if os.name == 'nt':
            import msvcrt
            print("\n>>> Siap di beranda Bitget? Tekan sembarang tombol (Q untuk STOP): ", end="", flush=True)
            ch = msvcrt.getch()
            if ch in (b'\x03', b'q', b'Q', b'\x1b'):
                print(" Q")
                print("\n[!] Alur dibatalkan oleh pengguna (STOP). Kembali ke menu utama...")
                self.stopped = True
                return False
            print(" [OK]")
        else:
            ans = input("\n>>> Siap di beranda Bitget? Tekan ENTER (Q untuk STOP): ").strip().lower()
            if ans == 'q':
                self.stopped = True
                return False

        # 5. Buat QRIS GoBiz Dinamis & Auto-Increment (+1)
        active_acc = get_active_gobiz_account(self.config)
        accs = get_gobiz_accounts(self.config)
        acc_idx = int(self.config.get("gobiz_active_index", 0)) % len(accs) if accs else 0
        rot_status = " (Shift Rotasi Otomatis)" if self.config.get("gobiz_shift_rotation", True) and len(accs) > 1 else ""
        print(f"\n[*] [SHIFT GOBIZ #{acc_idx + 1}/{len(accs)}] Menggunakan Akun: {active_acc.get('merchant_name', 'TOKO')}{rot_status}")

        target_amount = int(self.config.get("default_qris_nominal", 18501))
        ok_qr, qr_str, qr_det = self.qris_gen.create_and_save_qris(target_amount, TEMP_QR_PATH)
        if not ok_qr:
            print(f"[X] Gagal membuat QRIS: {qr_det.get('error')}")
            return False

        print(f"[V] QRIS Berhasil Dibuat: Rp {target_amount:,} | Merchant: {qr_det['merchant_name']}".replace(",", "."))

        # Auto-Increment: Naikkan +1 angka dan simpan ke config
        next_amount = target_amount + 1
        self.config["default_qris_nominal"] = next_amount
        save_config(self.config)
        print(f"[*] Nominal auto-increment (+1): Rp {next_amount:,} (Tersimpan untuk transaksi berikutnya)".replace(",", "."))

        if self.stopped:
            return False

        # 6. Push QR ke Device & Refresh Galeri
        ok_push, remote_qr = self.adb.push_qr_image(TEMP_QR_PATH)
        if not ok_push:
            print("[X] Gagal mengirim file QR ke HP.")
            return False

        if is_manual:
            if prompt_manual_step("Generate QRIS & Push Foto ke HP") == 'q':
                self.stopped = True
                return False

        # 7. Eksekusi Macro: Scan QR -> Galeri -> Pilih Foto -> Selesai
        print("\n[*] Menjalankan Macro Scan QRIS dari Galeri HP...")
        if not self.run_step_flow("1", "Scan QR Bitget", is_manual): return False
        if not self.run_step_flow("2", "Buka Galeri", is_manual): return False
        if not self.run_step_flow("3", "Pilih Foto QR", is_manual): return False
        if not self.run_step_flow("4", "Klik Selesai / Done", is_manual): return False

        # 8. Otomasi Pengambilan Alamat Tuyul via Deposit Sheet
        print("\n[*] Membuka Alur Deposit untuk Menyalin Alamat Tuyul...")
        if not self.run_step_flow("5", "Klik Deposit", is_manual): return False
        if not self.run_step_flow("6", "Pilih Terima Aset Kripto", is_manual): return False

        if not self.smart_sleep(0.5): return False
        screen_addr = self.adb.extract_evm_address_from_screen() if self.is_step_enabled("7") else ""
        if not self.run_step_flow("7", "Salin Address EVM Tuyul", is_manual): return False

        if not self.smart_sleep(0.5): return False
        clip_addr = self.adb.get_clipboard_text() if self.is_step_enabled("7") else ""

        tuyul_addr = screen_addr or clip_addr or get_last_tuyul_address()
        if tuyul_addr:
            save_last_tuyul_address(tuyul_addr)
        print(f"[*] Address Tuyul terdeteksi: {tuyul_addr or '(Kosong)'}")

        # Kembali ke Layar Tinjau Order (Back)
        if not self.run_step_flow("8", "Kembali ke Tinjau Order", is_manual): return False
        if not self.smart_sleep(1.0): return False

        if not (tuyul_addr and tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
            tuyul_addr = input("\n>>> Masukkan Address EVM Tuyul secara manual: ").strip()

        if not (tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
            print(f"[X] Address EVM tuyul tidak valid: '{tuyul_addr}'!")
            return False

        # 9. Baca Otomatis Nominal USDC dari Layar Tinjau Order (Jantung Inti Payment QRIS)
        print("\n[*] Mendeteksi nominal tagihan USDC dari layar HP...")
        detected_usdc = self.adb.read_required_usdc_from_screen()
        buffer_usdc = float(self.config.get("usdc_buffer", 0.0))

        if detected_usdc:
            usdc_needed = round(detected_usdc + buffer_usdc, 4)
            print(f"[V] Kebutuhan Layar : {detected_usdc} USDC")
            buf_str = f" (Termasuk buffer aman +{buffer_usdc})" if buffer_usdc > 0 else ""
            print(f"[V] Nominal Ditransfer : {usdc_needed} USDC{buf_str}")
        else:
            live_rate = self.adb.read_swap_rate_from_screen()
            if live_rate and live_rate > 1000:
                base_est = round(target_amount / live_rate, 4)
                print(f"[*] Kurs swap terdeteksi di layar: 1 USDC ≈ Rp {live_rate:,.2f}")
            else:
                safe_rate = float(self.config.get("fallback_rate", 17400.0))
                base_est = round(target_amount / safe_rate, 4)
                print(f"[*] Teks layar tidak terdeteksi, menggunakan kurs acuan aman: Rp {safe_rate:,.0f} / USDC ({base_est} USDC)")

            usdc_needed = round(base_est + buffer_usdc, 4)
            buf_str = f" (Termasuk buffer aman +{buffer_usdc})" if buffer_usdc > 0 else ""
            print(f"[V] Nominal Ditransfer : {usdc_needed} USDC{buf_str}")

        # 10. Kirim Saldo USDC Morph dari Wallet Tebar
        pk_tebar = self.config.get("wallet_tebar", {}).get("private_key")
        if not pk_tebar:
            print("\n[!] PERINGATAN: Private Key wallet_tebar belum diatur di config.json!")
            pk_in = input(">>> Masukkan Private Key Wallet Tebar (atau ENTER untuk skip): ").strip()
            if pk_in:
                self.wallet.set_private_key(pk_in)
                self.config["wallet_tebar"]["private_key"] = pk_in
                save_config(self.config)

        if self.wallet.private_key:
            print(f"\n[*] Mengirim {usdc_needed} USDC (Morph L2) ke {tuyul_addr}...")
            try:
                tx_res = self.wallet.send_usdc(tuyul_addr, usdc_needed)
            except Exception as e:
                tx_res = {"success": False, "error": f"Exception: {e}"}

            if tx_res.get("success"):
                print(f"[V] Berhasil transfer {usdc_needed} USDC Morph ke tuyul!")
                print(f"    Tx Hash : {tx_res.get('tx_hash')}")
                print(f"    Explorer: {tx_res.get('explorer')}")
                if not is_manual:
                    print("[*] Menunggu 4 detik agar saldo masuk...")
                    if not self.smart_sleep(4.0): return False
            else:
                print(f"[X] Transfer USDC Morph gagal: {tx_res.get('error')}")
                if is_manual:
                    c_ans = get_key_press(" Lanjutkan pembayaran di HP? [Y/n]: ").strip().lower()
                    if c_ans == 'n':
                        return False

        if is_manual:
            if prompt_manual_step("Auto-Tebar Saldo USDC Morph ke Tuyul") == 'q':
                return False

        # 11. Refresh Token, Konfirmasi Pembayaran & Input PIN
        print("\n[*] Menjalankan Refresh Token & Konfirmasi Pembayaran (Step 9)...")
        if not self.run_step_flow("9", "Refresh Token & Konfirmasi Pembayaran", is_manual): return False

        print("\n[*] Memasukkan PIN Transaksi (Step 10)...")
        if not self.run_step_flow("10", "Input PIN 080808", is_manual): return False

        # 12. Masuk Event Cashback & Claim Reward
        print("\n[*] Menunggu transaksi selesai & klaim cashback reward...")
        if not is_manual:
            if not self.smart_sleep(3.5): return False
        if not self.run_step_flow("11", "Masuk Event Cashback", is_manual): return False

        if not self.run_step_flow("12", "Claim Reward", is_manual): return False

        print("\n" + "="*70)
        print(f" [SELESAI] Eksekusi {mode_label} Berhasil Sukses!")
        print("="*70 + "\n")

        # Rotasi Shift Akun GoBiz untuk siklus berikutnya
        rotate_gobiz_shift(self.config, save_config)

        return True

    def run_rekam_delay(self):
        """Mode Rekam Delay HP secara 1 SIKLUS PENUH (termasuk Payment QRIS & Tebar Saldo)."""
        self.stopped = False
        self.is_manual = False
        self.config = load_config()
        clone_key = self.config.get("clone_app", "dual_space")
        clone_info = CLONE_APPS.get(clone_key, CLONE_APPS["dual_space"])
        current_nominal = int(self.config.get("default_qris_nominal", 18501))

        clear_screen()
        print("="*70)
        print("     MODE REKAM DELAY MASTER — 1 SIKLUS PENUH (kordinat_qris_morph.txt)")
        print(f"     Mode Clone Aktif : {clone_info['name']} ({clone_info['package']})")
        print(f"     Nominal QRIS     : Rp {current_nominal:,}".replace(",", "."))
        print("="*70)
        print("  Cara kerja:")
        print("  1. Bot menjalankan alur nyata 1 siklus penuh (termasuk pembayaran QRIS).")
        print("  2. Pada setiap step, aksi ADB dijalankan tanpa jeda sleep.")
        print("  3. Stopwatch timer langsung dimulai setelah aksi selesai.")
        print("  4. Tekan ENTER saat layar HP sudah siap ke langkah berikutnya.")
        print("     Durasi akan otomatis disimpan ke kordinat_qris_morph.txt!")
        print("  5. Ketik 'S' untuk SKIP step (delay lama dipertahankan).")
        print("  6. Ketik 'Q' untuk BERHENTI merekam.")
        print("="*70)

        # 1. Pastikan Device Terhubung
        if not self.adb.check_connection():
            print("[X] ERROR: Tidak ada perangkat HP Android terdeteksi via ADB!")
            return False

        # 2. Resolusi Layar Standar
        register_auto_restore()
        record_and_apply_bot_screen()

        recorded = {}

        def record_single_step(step_id: str, label: str) -> str:
            """Menjalankan action step tanpa sleep, menghitung waktu tunggu user, dan menyimpan delay."""
            if not self.is_step_enabled(step_id):
                print(f"\n[*] Step {step_id} ({label}) diatur OFF (dilewati).")
                return 'skip'

            step_data = None
            for s in parse_macro_steps():
                if str(s["id"]) == str(step_id):
                    step_data = s
                    break

            if not step_data:
                print(f"[!] Step {step_id} tidak ditemukan.")
                return 'skip'

            print(f"\n[>] Menjalankan Aksi Step [{step_id}. {step_data['name']}]...")
            for cmd in step_data["commands"]:
                self._run_single_command(cmd, skip_sleep=True)

            t_start = time.time()
            prompt_msg = f"  --> [REKAM DELAY] Tekan ENTER saat layar HP siap (S=Skip | Q=Berhenti): "
            sys.stdout.write(prompt_msg)
            sys.stdout.flush()

            user_key = 'enter'
            if os.name == 'nt':
                import msvcrt
                while True:
                    try:
                        ch = msvcrt.getch()
                    except KeyboardInterrupt:
                        user_key = 'q'
                        break
                    if ch in (b'\r', b'\n', b' ', b'\x16'):
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

            elapsed = max(round(time.time() - t_start, 1), 0.3)

            if user_key == 'q':
                print("\n[X] Rekaman dihentikan oleh pengguna.")
                return 'q'
            elif user_key == 's':
                print(f"  [--] Step {step_id} di-SKIP, delay lama dipertahankan.")
                return 'skip'

            update_sleep_in_kordinat(step_id, elapsed)
            recorded[step_id] = elapsed
            print(f"  [V] Delay Step {step_id} direkam: {elapsed}s -> disimpan ke file!")
            return 'ok'

        # Opsi Reset Clone sebelum rekam
        print("\n[?] Apakah ingin Reset Cache & Buka Clone sebelum mulai merekam?")
        print("    [Y] Ya, Reset Atomik Clone & Rekam Delay ID Iklan (GAID)")
        print("    [N] Tidak, saya sudah siap di Beranda Bitget Wallet HP")
        p_rst = get_key_press(" Pilihan [Y/n]: ").strip().lower()
        if p_rst != 'n':
            print("\n" + "="*60)
            print(f" MEMULAI RESET ATOMIK CLONE: {clone_info['name']}")
            print("="*60)
            self.adb.force_stop_and_clear_cache(clone_key, stop_checker=self.is_stopped)

            print("\n[*] [FASE 0] MEREKAM DELAY RESET ID IKLAN (GOOGLE ADVERTISING ID)...")
            gaid_steps = [
                ("0.1", "Buka Pengaturan Iklan Google"),
                ("0.2", "Ketuk Delete Advertising ID"),
                ("0.3", "Ketuk Tombol Hijau Delete Advertising ID"),
                ("0.4", "Ketuk Get New Advertising ID"),
                ("0.5", "Ketuk Confirm Dialog Get New ID"),
                ("0.6", "Ketuk Reset Advertising ID"),
                ("0.7", "Ketuk Confirm Dialog Reset ID"),
                ("0.8", "Tutup Pengaturan Iklan & Kembali")
            ]
            for sid, slbl in gaid_steps:
                res = record_single_step(sid, slbl)
                if res == 'q': return False

            airplane_sec = self.config.get("airplane_seconds", 3)
            self.adb.toggle_airplane_mode(airplane_sec, stop_checker=self.is_stopped)
            self.adb.launch_clone_app(clone_key, stop_checker=self.is_stopped)
            print("="*60 + "\n")

            print("\n" + "-"*70)
            print(" [ACTION] SILAKAN BUKA BITGET WALLET DI DALAM CLONE HP SAMPAI DI BERANDA")
            print("-"*70)
            wait_any_key(">>> Siap di beranda Bitget? Tekan ENTER untuk lanjut rekam: ")

        # 3. Buat QRIS GoBiz Dinamis & Push ke HP
        target_amount = int(self.config.get("default_qris_nominal", 18501))
        print(f"\n[*] Membuat QRIS GoBiz Dinamis: Rp {target_amount:,}...".replace(",", "."))
        ok_qr, qr_str, qr_det = self.qris_gen.create_and_save_qris(target_amount, TEMP_QR_PATH)
        if not ok_qr:
            print(f"[X] Gagal membuat QRIS: {qr_det.get('error')}")
            return False

        # Auto-Increment
        self.config["default_qris_nominal"] = target_amount + 1
        save_config(self.config)

        ok_push, remote_qr = self.adb.push_qr_image(TEMP_QR_PATH)
        if not ok_push:
            print("[X] Gagal mengirim file QR ke HP.")
            return False

        # --- REKAM LANGKAH 1 s/d 4 (Scan QRIS Galeri) ---
        for sid, lbl in [
            ("1", "Scan QR Bitget"),
            ("2", "Buka Galeri"),
            ("3", "Pilih Foto QR"),
            ("4", "Klik Selesai / Done")
        ]:
            res = record_single_step(sid, lbl)
            if res == 'q': return False

        # --- REKAM LANGKAH 5 s/d 7 (Buka Deposit & Salin Address Tuyul) ---
        for sid, lbl in [
            ("5", "Klik Deposit"),
            ("6", "Pilih Terima Aset Kripto"),
            ("7", "Salin Address EVM Tuyul")
        ]:
            res = record_single_step(sid, lbl)
            if res == 'q': return False

        # Ekstrak Address Tuyul
        tuyul_addr = self.adb.extract_evm_address_from_screen() or self.adb.get_clipboard_text() or get_last_tuyul_address()
        if tuyul_addr:
            save_last_tuyul_address(tuyul_addr)
        print(f"\n[*] Address Tuyul terdeteksi: {tuyul_addr or '(Kosong)'}")

        # --- REKAM LANGKAH 8 (Kembali ke Tinjau Order) ---
        res = record_single_step("8", "Kembali ke Tinjau Order")
        if res == 'q': return False

        # --- JANTUNG INTI PAYMENT QRIS: TEBAR SALDO USDC MORPH ---
        print("\n" + "="*70)
        print("    [JANTUNG INTI PAYMENT QRIS] TEBAR SALDO USDC MORPH L2")
        print("="*70)
        print("[*] Mendeteksi nominal tagihan USDC dari layar HP...")
        detected_usdc = self.adb.read_required_usdc_from_screen()
        buffer_usdc = float(self.config.get("usdc_buffer", 0.0))

        if detected_usdc:
            usdc_needed = round(detected_usdc + buffer_usdc, 4)
            print(f"[V] Kebutuhan Layar : {detected_usdc} USDC")
        else:
            live_rate = self.adb.read_swap_rate_from_screen()
            if live_rate and live_rate > 1000:
                base_est = round(target_amount / live_rate, 4)
            else:
                safe_rate = float(self.config.get("fallback_rate", 17400.0))
                base_est = round(target_amount / safe_rate, 4)
            usdc_needed = round(base_est + buffer_usdc, 4)
            print(f"[*] Teks layar tidak terdeteksi, estimasi tagihan: {usdc_needed} USDC")

        buf_str = f" (Termasuk buffer aman +{buffer_usdc})" if buffer_usdc > 0 else ""
        print(f"[V] Nominal Ditransfer : {usdc_needed} USDC{buf_str}")

        if not (tuyul_addr and tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
            tuyul_addr = input("\n>>> Masukkan Address EVM Tuyul: ").strip()

        if self.wallet.private_key and tuyul_addr:
            print(f"\n[*] Mengirim {usdc_needed} USDC (Morph L2) ke {tuyul_addr}...")
            tx_res = self.wallet.send_usdc(tuyul_addr, usdc_needed)
            if tx_res.get("success"):
                print(f"[V] Berhasil transfer {usdc_needed} USDC Morph ke tuyul!")
                print(f"    Tx Hash : {tx_res.get('tx_hash')}")
                print(f"    Explorer: {tx_res.get('explorer')}")
            else:
                print(f"[X] Transfer USDC Morph gagal: {tx_res.get('error')}")

        # Stopwatch tunggu saldo masuk ke Tuyul
        t_saldo = time.time()
        sys.stdout.write("\n  --> [REKAM DELAY] Menunggu saldo masuk ke Tuyul di HP... Tekan ENTER saat saldo terisi: ")
        sys.stdout.flush()
        if os.name == 'nt':
            import msvcrt
            while True:
                ch = msvcrt.getch()
                if ch in (b'\r', b'\n', b' ', b'\x16'):
                    sys.stdout.write(" [ENTER]\n")
                    sys.stdout.flush()
                    break
                elif ch in (b'q', b'Q'):
                    return False
        else:
            input()
        elapsed_saldo = round(time.time() - t_saldo, 1)
        print(f"  [V] Waktu tunggu saldo masuk tercatat: {elapsed_saldo}s")

        # --- REKAM LANGKAH 9 s/d 12 (Konfirmasi Pembayaran, PIN, Cashback & Claim) ---
        for sid, lbl in [
            ("9", "Refresh Token & Klik Konfirmasi Pembayaran"),
            ("10", "Input PIN Transaksi"),
            ("11", "Klik Masuk Event Cashback"),
            ("12", "Klik Claim Reward")
        ]:
            res = record_single_step(sid, lbl)
            if res == 'q': return False

        print("\n" + "="*70)
        print(f"  REKAMAN 1 SIKLUS PENUH SELESAI — {len(recorded)} delay berhasil diperbarui!")
        if recorded:
            for sid, val in recorded.items():
                print(f"    - Step {sid}: {val}s")
        print("="*70)
        print("  Delay baru telah tersimpan permanen ke kordinat_qris_morph.txt.")
        print("  Jalankan MODE FULL AUTO (Menu 1) untuk memakai delay baru ini.\n")
        return True

def get_scrcpy_exe():
    candidates = [
        os.path.join(CORE_DIR, "scrcpy-win64-v3.3.4", "scrcpy.exe"),
        r"C:\Users\KAGE\Desktop\scrcpy-win64-v3.3.4\scrcpy.exe",
        os.path.join(os.path.expanduser("~"), "Desktop", "scrcpy-win64-v3.3.4", "scrcpy.exe"),
        r"C:\Users\KAGE\Desktop\PROJECT BOT IMAM\COINS_PAYMENT_GATEWAY\core\scrcpy-win64-v3.3.4\scrcpy.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return shutil.which("scrcpy.exe") or shutil.which("scrcpy")

def launch_mirror_screen(extra_args=""):
    scrcpy_exe = get_scrcpy_exe()
    if scrcpy_exe:
        print("[*] Menjalankan scrcpy mirror (Layar fisik HP mati: -S -w)...")
        flags = extra_args.strip()
        if "-S" not in flags:
            flags = f"{flags} -S -w".strip()
        cmd = f'start "" "{scrcpy_exe}" {flags}'.strip() if os.name == 'nt' else f'"{scrcpy_exe}" {flags} &'
        os.system(cmd)
    else:
        print("[!] File scrcpy.exe tidak ditemukan!")

def get_windows_clipboard_text() -> str:
    try:
        res = subprocess.check_output(['powershell', '-NoProfile', '-Command', 'Get-Clipboard'], text=True, stderr=subprocess.DEVNULL)
        if res.strip():
            return res.strip()
    except Exception:
        pass
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if user32.OpenClipboard(None):
            h_glb = user32.GetClipboardData(13)
            if h_glb:
                kernel32.GlobalLock.restype = ctypes.c_wchar_p
                ptr = kernel32.GlobalLock(h_glb)
                txt = str(ptr) if ptr else ""
                kernel32.GlobalUnlock(h_glb)
                user32.CloseClipboard()
                return txt
            user32.CloseClipboard()
    except Exception:
        pass
    return ""

def menu_select_clone_app():
    cfg = load_config()
    current = cfg.get("clone_app", "dual_space")

    clear_screen()
    print("="*65)
    print("          PILIH APLIKASI CLONE TARGET (INSTAN)")
    print("="*65)
    print(f" Aplikasi saat ini: {CLONE_APPS.get(current, {}).get('name', current)}\n")

    print(" [1] Dual Space   (com.xunijun.app.gp)")
    print(" [2] Multiple App (com.multipleapp.clonespace)")
    print(" [3] Multi App    (com.waxmoon.ma.gp)")
    print(" [0] Kembali")
    print("="*65)

    pilihan = get_key_press(" Pilih target clone [0-3]: ").strip()
    mapping = {
        "1": "dual_space",
        "2": "multiple_app",
        "3": "multi_app"
    }
    if pilihan in mapping:
        cfg["clone_app"] = mapping[pilihan]
        save_config(cfg)
        selected_name = CLONE_APPS[mapping[pilihan]]["name"]
        print(f"\n[V] Berhasil diatur ke: {selected_name}!")
        time.sleep(1.0)

def menu_screen_settings():
    clear_screen()
    print("="*65)
    print("        PENGELOLAAN RESOLUSI & DPI LAYAR HP (INSTAN)")
    print("="*65)

    info = read_current_screen()
    cached_s, cached_d = get_cached_screen()

    print(f" Resolusi Aktif Layar HP : {info.get('active_size')} @ {info.get('active_density')} DPI")
    print(f" Ukuran Fisik Hardware  : {info.get('physical_size')} @ {info.get('physical_density')} DPI")
    print(f" Ukuran Asli Terekam    : {cached_s or '(Belum direkam)'} @ {cached_d or '-'} DPI\n")

    print(" [1] Pasang Resolusi Standar Bot (1080x2400 @ 352 DPI)")
    print(" [2] Kembalikan ke Ukuran Asli HP yang Terekam")
    print(" [3] Rekam Ulang Ukuran Asli Layar HP Saat Ini")
    print(" [0] Kembali")
    print("="*65)

    pilihan = get_key_press(" Pilih opsi [0-3]: ").strip()
    if pilihan == "1":
        ok, msg = record_and_apply_bot_screen()
        print(f"\n[V] {msg}")
        wait_any_key()
    elif pilihan == "2":
        restore_recorded_screen()
        wait_any_key()
    elif pilihan == "3":
        if os.path.exists(os.path.join(CORE_DIR, '.screen_cache.json')):
            os.remove(os.path.join(CORE_DIR, '.screen_cache.json'))
        ok, msg = record_and_apply_bot_screen()
        print(f"\n[V] Berhasil direkam ulang: {msg}")
        wait_any_key()

def menu_wallet_and_token():
    cfg = load_config()
    wt_cfg = cfg.get("wallet_tebar", {})
    wallet = MorphWallet(
        private_key=wt_cfg.get("private_key"),
        custom_rpc=cfg.get("morph", {}).get("rpc_url")
    )

    clear_screen()
    print("="*65)
    print("         DOMPET TEBAR - SALDO & TRANSFER MORPH L2")
    print("="*65)
    print(f" Address Wallet Tebar : {wallet.address or wt_cfg.get('address') or '(Belum diisi)'}")
    print(f" Status Private Key   : {'Sudah Diatur' if wallet.private_key else 'KOSONG / Belum Diisi'}\n")

    addr_target = wallet.address or wt_cfg.get("address")
    if addr_target:
        print("[*] Mengambil saldo dari node Morph L2...")
        bals = wallet.get_balances(addr_target)
        if bals.get("success"):
            print(f" - Saldo Gas (ETH) : {bals['eth_balance']:.6f} ETH")
            print(f" - Saldo USDC Morph: {bals['usdc_balance']:.4f} USDC")
        else:
            print(f"[!] Gagal cek saldo: {bals.get('error')}")
    print("="*65)
    print(" [1] Atur / Ganti Private Key Wallet Tebar")
    print(" [2] Test Transfer USDC Morph ke Address Tertentu")
    print(" [3] Cek Saldo Address Lain")
    print(" [0] Kembali")
    print("="*65)

    pilihan = get_key_press(" Pilih opsi [0-3]: ").strip()
    if pilihan == "1":
        pk_in = input("\n Masukkan Private Key (0x...): ").strip()
        if pk_in:
            ok, res_addr = wallet.set_private_key(pk_in)
            if ok:
                cfg.setdefault("wallet_tebar", {})["private_key"] = pk_in
                cfg["wallet_tebar"]["address"] = res_addr
                save_config(cfg)
                print(f"[V] Private key berhasil disimpan! Address: {res_addr}")
            else:
                print(f"[X] Gagal: {res_addr}")
            wait_any_key()
    elif pilihan == "2":
        if not wallet.private_key:
            print("\n[!] Private key belum diisi! Silakan isi private key terlebih dahulu.")
            wait_any_key()
            return
        to_addr = input("\n Masukkan address tujuan: ").strip()
        amt_str = input(" Masukkan nominal USDC: ").strip()
        try:
            amt = float(amt_str)
            res = wallet.send_usdc(to_addr, amt)
            if res.get("success"):
                print(f"\n[V] Transfer Sukses! Tx: {res.get('tx_hash')}")
            else:
                print(f"\n[X] Transfer Gagal: {res.get('error')}")
        except ValueError:
            print("[X] Nominal tidak valid.")
        wait_any_key()
    elif pilihan == "3":
        addr_in = input("\n Masukkan address target: ").strip()
        bals = wallet.get_balances(addr_in)
        if bals.get("success"):
            print(f" - ETH  : {bals['eth_balance']:.6f} ETH")
            print(f" - USDC : {bals['usdc_balance']:.4f} USDC")
        else:
            print(f"[X] Error: {bals.get('error')}")
        wait_any_key()

def _do_generate_and_push(cfg, amount):
    generator = GoBizQRISGenerator(cfg)
    adb = ADBController()
    out_file = TEMP_QR_PATH

    print(f"\n[*] Menghasilkan QRIS GoBiz dinamis Rp {amount:,}...")
    ok, qr_str, det = generator.create_and_save_qris(amount, out_file)
    if ok:
        print(f"[V] QRIS Berhasil Dibuat!")
        print(f" - Mode Engine : {det.get('mode', 'STANDALONE')}")
        print(f" - Merchant    : {det.get('merchant_name')}")
        print(f" - Kota        : {det.get('city')}")
        print(f" - NMID        : {det.get('nmid', '-')}")
        if det.get("order_id"):
            print(f" - Order ID    : {det.get('order_id')}")
        print(f" - File PNG    : {out_file}")

        next_amount = amount + 1
        cfg["default_qris_nominal"] = next_amount
        save_config(cfg)
        print(f"[*] Nominal berikutnya otomatis dinaikkan (+1): Rp {next_amount:,} (Tersimpan di config)".replace(",", "."))

        print("\n [Y] Push gambar QR langsung ke HP sekarang")
        print(" [N] Jangan push, simpan file saja")
        ans = get_key_press(" Pilihan [Y/n]: ").strip().lower()
        if ans != 'n':
            ok_push, remote_p = adb.push_qr_image(out_file)
            if ok_push:
                print(f"[V] Gambar QR sudah tersedia di Galeri HP: {remote_p}")
    else:
        print(f"[X] Gagal membuat QRIS: {det.get('error')}")
    wait_any_key()

def menu_gobiz_credentials():
    while True:
        cfg = load_config()
        accounts = get_gobiz_accounts(cfg)
        active_idx = int(cfg.get("gobiz_active_index", 0)) % len(accounts) if accounts else 0
        active_acc = get_active_gobiz_account(cfg)
        is_rotation_on = cfg.get("gobiz_shift_rotation", True)

        clear_screen()
        print("="*65)
        print("         PENGELOLAAN MULTI-AKUN GOBIZ & SHIFT ROTASI")
        print("="*65)
        rot_label = "[ AKTIF (Selang-Seling Tiap Siklus) ]" if is_rotation_on else "[ NON-AKTIF (Terkunci di Akun Pilihan) ]"
        print(f" Status Shift Rotasi : {rot_label}")
        print(f" Total Akun Terdaftar: {len(accounts)} Akun\n")
        print(" DAFTAR AKUN GOBIZ:")
        print("-" * 65)
        if not accounts:
            print("  (Belum ada akun GoBiz yang terdaftar)")
        else:
            for idx, acc in enumerate(accounts):
                is_active = (idx == active_idx)
                marker = "[*] AKTIF BERTUGAS" if is_active else "[ ]"
                acc_name = acc.get("account_name") or acc.get("merchant_name") or f"Akun #{idx+1}"
                city = acc.get("city") or "KOTA"
                sk = acc.get("server_key", "")
                mode_stat = "Midtrans API Terhubung" if sk else "Standalone Offline"
                print(f" {marker} Akun #{idx+1}: {acc_name} ({city})")
                print(f"     -> Outlet ID: {str(acc.get('outlet_id', '-'))[:18]}... | Status: {mode_stat}")
        print("="*65)
        print(" [1] Tambah Akun via Clipboard Windows (Copy cURL/Token -> Tekan 1)")
        print(" [2] Tambah Akun via Input Keyboard Manual (Paste Token/cURL)")
        print(" [3] Pilih Akun Aktif Manual (Kunci Akun Tertentu)")
        print(" [4] Toggle Rotasi Shift Otomatis (ON / OFF)")
        print(" [5] Sync Ulang Semua Data Toko dari Server GoBiz")
        print(" [6] Hapus Salah Satu Akun dari Daftar")
        print(" [7] Toggle Acak Nama Merchant (Stealth vs Nama Asli)")
        print(" [0] Kembali ke Menu Sebelumnya")
        print("="*65)

        p = get_key_press(" Pilih opsi [0-7]: ").strip()
        if p == "0":
            break
        elif p == "1":
            print("\n[*] Membaca data cURL / Token dari Clipboard Windows...")
            clip_data = get_windows_clipboard_text()
            if not clip_data:
                print("[!] Clipboard Windows kosong atau tidak dapat diakses.")
                time.sleep(1.5)
            else:
                clean_tok = extract_token_from_input(clip_data)
                if not clean_tok:
                    print("[!] Tidak ditemukan token atau cURL yang valid di clipboard Windows.")
                    time.sleep(2.0)
                else:
                    print(f"[*] Token terdeteksi dari Clipboard: {clean_tok[:18]}...")
                    print("[*] Menghubungi server GoBiz untuk verifikasi toko...")
                    res = fetch_gobiz_merchant_info(clean_tok)
                    if res.get("success"):
                        new_acc = {
                            "account_name": res.get("merchant_name") or f"Akun GoBiz #{len(accounts) + 1}",
                            "mode": "api",
                            "raw_qris": res.get("raw_qris", ""),
                            "merchant_id": res.get("merchant_id", ""),
                            "outlet_id": res.get("outlet_id", ""),
                            "pop_id": res.get("pop_id", ""),
                            "server_key": res.get("server_key", ""),
                            "client_key": res.get("client_key", ""),
                            "auth_token": clean_tok,
                            "merchant_name": res.get("merchant_name", "TOKO GOBIZ"),
                            "city": res.get("city", "INDONESIA"),
                            "auto_random_merchant": True
                        }
                        found_idx = -1
                        for i, existing in enumerate(accounts):
                            if (new_acc["outlet_id"] and existing.get("outlet_id") == new_acc["outlet_id"]) or \
                               (new_acc["merchant_id"] and existing.get("merchant_id") == new_acc["merchant_id"]):
                                found_idx = i
                                break
                        if found_idx >= 0:
                            accounts[found_idx] = new_acc
                            print(f"\n[V] Akun #{found_idx + 1} berhasil diperbarui: {new_acc['merchant_name']} ({new_acc['city']})")
                        else:
                            accounts.append(new_acc)
                            print(f"\n[V] Akun #{len(accounts)} berhasil ditambahkan: {new_acc['merchant_name']} ({new_acc['city']})")
                        cfg["gobiz_accounts"] = accounts
                        cfg["gobiz"] = accounts[active_idx]
                        save_config(cfg)
                    else:
                        print(f"[X] Gagal verifikasi GoBiz: {res.get('error')}")
                    wait_any_key("\n Tekan sembarang tombol untuk melanjutkan...")
        elif p == "2":
            new_input = input("\n Paste Token JWT atau cURL Perintah GoBiz: ").strip()
            if new_input:
                clean_tok = extract_token_from_input(new_input)
                if clean_tok:
                    print(f"[*] Token diekstrak: {clean_tok[:18]}...")
                    print("[*] Menghubungi server GoBiz untuk verifikasi toko...")
                    res = fetch_gobiz_merchant_info(clean_tok)
                    if res.get("success"):
                        new_acc = {
                            "account_name": res.get("merchant_name") or f"Akun GoBiz #{len(accounts) + 1}",
                            "mode": "api",
                            "raw_qris": res.get("raw_qris", ""),
                            "merchant_id": res.get("merchant_id", ""),
                            "outlet_id": res.get("outlet_id", ""),
                            "pop_id": res.get("pop_id", ""),
                            "server_key": res.get("server_key", ""),
                            "client_key": res.get("client_key", ""),
                            "auth_token": clean_tok,
                            "merchant_name": res.get("merchant_name", "TOKO GOBIZ"),
                            "city": res.get("city", "INDONESIA"),
                            "auto_random_merchant": True
                        }
                        found_idx = -1
                        for i, existing in enumerate(accounts):
                            if (new_acc["outlet_id"] and existing.get("outlet_id") == new_acc["outlet_id"]) or \
                               (new_acc["merchant_id"] and existing.get("merchant_id") == new_acc["merchant_id"]):
                                found_idx = i
                                break
                        if found_idx >= 0:
                            accounts[found_idx] = new_acc
                            print(f"\n[V] Akun #{found_idx + 1} berhasil diperbarui: {new_acc['merchant_name']} ({new_acc['city']})")
                        else:
                            accounts.append(new_acc)
                            print(f"\n[V] Akun #{len(accounts)} berhasil ditambahkan: {new_acc['merchant_name']} ({new_acc['city']})")
                        cfg["gobiz_accounts"] = accounts
                        cfg["gobiz"] = accounts[active_idx]
                        save_config(cfg)
                    else:
                        print(f"[X] Gagal verifikasi GoBiz: {res.get('error')}")
                else:
                    print("[!] Token atau cURL tidak valid.")
                wait_any_key("\n Tekan sembarang tombol untuk melanjutkan...")
        elif p == "3":
            if not accounts:
                print("\n[!] Belum ada akun yang terdaftar.")
                time.sleep(1.5)
            else:
                pilih_acc = input(f"\n Masukkan nomor akun yang ingin dijadikan aktif [1-{len(accounts)}]: ").strip()
                if pilih_acc.isdigit():
                    idx_pilih = int(pilih_acc) - 1
                    if 0 <= idx_pilih < len(accounts):
                        cfg["gobiz_active_index"] = idx_pilih
                        cfg["gobiz"] = accounts[idx_pilih]
                        save_config(cfg)
                        print(f"[V] Akun aktif berhasil diubah ke #{idx_pilih + 1}: {accounts[idx_pilih].get('merchant_name')}")
                        time.sleep(1.5)
                    else:
                        print("[X] Nomor akun di luar rentang.")
                        time.sleep(1.0)
        elif p == "4":
            curr_rot = cfg.get("gobiz_shift_rotation", True)
            cfg["gobiz_shift_rotation"] = not curr_rot
            save_config(cfg)
            stat = "AKTIF (Selang-Seling Tiap Siklus Transaksi)" if not curr_rot else "NON-AKTIF"
            print(f"\n[V] Rotasi Shift sekarang: {stat}")
            time.sleep(1.5)
        elif p == "5":
            if not accounts:
                print("\n[!] Belum ada akun yang terdaftar.")
                time.sleep(1.5)
            else:
                print("\n[*] Menyinkronkan seluruh akun GoBiz...")
                for idx, acc in enumerate(accounts):
                    tok = acc.get("auth_token", "")
                    if tok:
                        print(f" -> Sinkronisasi Akun #{idx + 1} ({acc.get('merchant_name', 'TOKO')})...")
                        res = fetch_gobiz_merchant_info(tok)
                        if res.get("success"):
                            acc["server_key"] = res["server_key"]
                            acc["pop_id"] = res["pop_id"]
                            acc["outlet_id"] = res["outlet_id"]
                            acc["merchant_name"] = res["merchant_name"]
                            acc["city"] = res["city"]
                            if res.get("raw_qris"):
                                acc["raw_qris"] = res["raw_qris"]
                            print(f"    [V] Sukses: {res['merchant_name']} ({res['city']})")
                        else:
                            print(f"    [X] Gagal: {res.get('error')}")
                cfg["gobiz_accounts"] = accounts
                cfg["gobiz"] = accounts[active_idx]
                save_config(cfg)
                wait_any_key("\n Selesai sinkronisasi. Tekan sembarang tombol...")
        elif p == "6":
            if not accounts:
                print("\n[!] Tidak ada akun yang bisa dihapus.")
                time.sleep(1.5)
            else:
                del_str = input(f"\n Masukkan nomor akun yang ingin dihapus [1-{len(accounts)}]: ").strip()
                if del_str.isdigit():
                    del_idx = int(del_str) - 1
                    if 0 <= del_idx < len(accounts):
                        removed = accounts.pop(del_idx)
                        cfg["gobiz_accounts"] = accounts
                        if active_idx >= len(accounts):
                            active_idx = max(0, len(accounts) - 1)
                        cfg["gobiz_active_index"] = active_idx
                        if accounts:
                            cfg["gobiz"] = accounts[active_idx]
                        else:
                            cfg["gobiz"] = {}
                        save_config(cfg)
                        print(f"[V] Akun '{removed.get('merchant_name')}' berhasil dihapus.")
                        time.sleep(1.5)
                    else:
                        print("[X] Nomor akun di luar rentang.")
                        time.sleep(1.0)
        elif p == "7":
            if accounts:
                curr_stealth = accounts[active_idx].get("auto_random_merchant", True)
                new_stealth = not curr_stealth
                for acc in accounts:
                    acc["auto_random_merchant"] = new_stealth
                cfg.setdefault("gobiz", {})["auto_random_merchant"] = new_stealth
                save_config(cfg)
                stat = "AKTIF (Stealth Acak)" if new_stealth else "NON-AKTIF (Nama Asli Toko)"
                print(f"\n[V] Acak nama merchant sekarang: {stat}")
                time.sleep(1.5)

def menu_generate_qris():
    while True:
        cfg = load_config()
        accounts = get_gobiz_accounts(cfg)
        active_idx = int(cfg.get("gobiz_active_index", 0)) % len(accounts) if accounts else 0
        active_acc = get_active_gobiz_account(cfg)
        current_mode = (active_acc.get("mode") or "api").upper()
        server_key_set = bool(active_acc.get("server_key"))
        default_nom = int(cfg.get("default_qris_nominal", 18501))
        rot_on = cfg.get("gobiz_shift_rotation", True)

        clear_screen()
        print("="*65)
        print("        GENERATOR GOBIZ QRIS & PUSH KE GALERI HP")
        print("="*65)
        engine_label = "[API MIDTRANS RESMI]" if (current_mode == "API" and server_key_set) else "[STANDALONE OFFLINE]"
        rot_lbl = " (Shift Rotasi Otomatis AKTIF)" if rot_on and len(accounts) > 1 else ""
        print(f" Mode Engine    : {engine_label}")
        print(f" Merchant Aktif : Akun #{active_idx + 1}: {active_acc.get('merchant_name', 'TOKO GOBIZ MERCHANT')}{rot_lbl}")
        print(f" Nominal Default: Rp {default_nom:,}".replace(",", "."))
        print("="*65)
        print(f" [1] Generate QRIS Nominal Standar (Rp {default_nom:,})".replace(",", "."))
        print(f" [2] Set Nominal Default Baru (Sekarang: Rp {default_nom:,})".replace(",", "."))
        print(f" [3] Ganti Mode Engine (Sekarang: {current_mode})")
        print(f" [4] Atur Multi-Akun GoBiz & Shift Rotasi ({len(accounts)} Akun Terdaftar)")
        print(" [0] Kembali ke Menu Sebelumnya")
        print("="*65)

        sub_pil = get_key_press(" Pilih opsi [0-4]: ").strip()
        if sub_pil == "0":
            break
        elif sub_pil == "1":
            _do_generate_and_push(cfg, default_nom)
        elif sub_pil == "2":
            print(f"\n[*] Nominal default saat ini: Rp {default_nom:,}".replace(",", "."))
            nom_str = input(" Masukkan nominal default baru dalam Rupiah (contoh: 18501): ").strip()
            if nom_str.isdigit() and int(nom_str) > 0:
                new_nom = int(nom_str)
                cfg["default_qris_nominal"] = new_nom
                save_config(cfg)
                print(f"\n[V] Nominal default berhasil diperbarui menjadi: Rp {new_nom:,}".replace(",", "."))
                print(" [Y] Langsung Generate & Push QRIS ke HP Sekarang")
                print(" [N] Simpan Saja & Kembali")
                ask = get_key_press(" Pilihan [Y/n]: ").strip().lower()
                if ask != 'n':
                    _do_generate_and_push(cfg, new_nom)
                else:
                    time.sleep(0.8)
            else:
                print("[!] Input tidak valid. Nominal harus berupa angka positif.")
                time.sleep(1.0)
        elif sub_pil == "3":
            new_mode = "standalone" if current_mode == "API" else "api"
            active_acc["mode"] = new_mode
            if accounts:
                accounts[active_idx]["mode"] = new_mode
                cfg["gobiz_accounts"] = accounts
            cfg.setdefault("gobiz", {})["mode"] = new_mode
            save_config(cfg)
            print(f"\n[V] Mode GoBiz diubah ke: {new_mode.upper()}!")
            time.sleep(1.0)
        elif sub_pil == "4":
            menu_gobiz_credentials()

def menu_toggle_steps():
    """Pengaturan ON / OFF Step Koordinat Macro (kordinat_qris_morph.txt)."""
    execute_toggle_steps_logic(KORDINAT_FILE, DISABLED_CONFIG_KEY)

def menu_manage_steps():
    """Menu untuk melihat dan menguji langkah koordinat kordinat_qris_morph.txt."""
    runner = BotRunner()
    key_mapping = {
        "j": "0.1",
        "k": "0.2",
        "l": "0.3",
        "m": "0.4",
        "o": "0.5",
        "u": "0.6",
        "v": "0.7",
        "w": "0.8",
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
        "5": "5",
        "6": "6",
        "7": "7",
        "8": "8",
        "9": "9",
        "a": "10",
        "b": "11",
        "c": "12",
    }

    last_tested_msg = ""

    while True:
        clear_screen()
        print("="*70)
        print("      TEST KOORDINAT MACRO INSTAN (TETAP DI MENU TEST)")
        print("   Tekan angka / huruf langsung dieksekusi seketika tanpa ENTER!")
        print("="*70)
        steps = parse_macro_steps()
        step_map = {str(s["id"]): s for s in steps}

        def _st(sid):
            return "[OFF ]" if step_map.get(sid, {}).get("is_off") else "[ ON ]"

        print(f" [J] Step 0.1 {_st('0.1')} : {step_map.get('0.1', {}).get('name', 'Buka Pengaturan Iklan Google')}")
        print(f" [K] Step 0.2 {_st('0.2')} : {step_map.get('0.2', {}).get('name', 'Ketuk Delete Advertising ID')}")
        print(f" [L] Step 0.3 {_st('0.3')} : {step_map.get('0.3', {}).get('name', 'Ketuk Tombol Hijau Delete ID')}")
        print(f" [M] Step 0.4 {_st('0.4')} : {step_map.get('0.4', {}).get('name', 'Ketuk Get New Advertising ID')}")
        print(f" [O] Step 0.5 {_st('0.5')} : {step_map.get('0.5', {}).get('name', 'Ketuk Confirm Dialog Get New ID')}")
        print(f" [U] Step 0.6 {_st('0.6')} : {step_map.get('0.6', {}).get('name', 'Ketuk Reset Advertising ID')}")
        print(f" [V] Step 0.7 {_st('0.7')} : {step_map.get('0.7', {}).get('name', 'Ketuk Confirm Dialog Reset ID')}")
        print(f" [W] Step 0.8 {_st('0.8')} : {step_map.get('0.8', {}).get('name', 'Tutup Pengaturan Iklan & Kembali')}")
        print("-"*70)
        print(f" [1] Step 1   {_st('1')} : {step_map.get('1', {}).get('name', 'Scan QR Bitget')}")
        print(f" [2] Step 2   {_st('2')} : {step_map.get('2', {}).get('name', 'Galeri Scanner')}")
        print(f" [3] Step 3   {_st('3')} : {step_map.get('3', {}).get('name', 'Pilih Gambar QR')}")
        print(f" [4] Step 4   {_st('4')} : {step_map.get('4', {}).get('name', 'Selesai / Done')}")
        print(f" [5] Step 5   {_st('5')} : {step_map.get('5', {}).get('name', 'Tombol Deposit')}")
        print(f" [6] Step 6   {_st('6')} : {step_map.get('6', {}).get('name', 'Terima Aset Kripto')}")
        print(f" [7] Step 7   {_st('7')} : {step_map.get('7', {}).get('name', 'Salin Address EVM Tuyul')}")
        print(f" [8] Step 8   {_st('8')} : {step_map.get('8', {}).get('name', 'Kembali ke Tinjau Order (Back 2x)')}")
        print(" [D] Auto-Tebar  : Kirim Saldo USDC Morph (Baca Layar & Transfer On-Chain)")
        print(f" [9] Step 9   {_st('9')} : {step_map.get('9', {}).get('name', 'Pilih Token & Konfirmasi Pembayaran')}")
        print(f" [A] Step 10  {_st('10')} : {step_map.get('10', {}).get('name', 'Input PIN Transaksi')}")
        print(f" [B] Step 11  {_st('11')} : {step_map.get('11', {}).get('name', 'Masuk Event Cashback')}")
        print(f" [C] Step 12  {_st('12')} : {step_map.get('12', {}).get('name', 'Claim Reward')}")
        print("-"*70)
        print(" [E] Sub-Tap : Klik Kolom Jumlah Pembayaran Saja (916 1594)")
        print(" [F] Sub-Tap : Pilih Token USDC Morph Paling Atas Saja (517 1536)")
        print(" [G] Sub-Tap : Klik Tombol Konfirmasi Pembayaran Saja (540 2193)")
        print(" [P] Sub-Tap : Ketik Sandi PIN 080808 Saja")
        print(" [I] Sub-Tap : Jalankan Alur Lengkap Reset GAID (Step 0.1 s/d 0.8)")
        print(" [T] Atur ON / OFF Step Koordinat Macro (kordinat_qris_morph.txt)")
        print(" [N] Buka / Edit File kordinat_qris_morph.txt di Notepad")
        print(" [0] Kembali ke Menu Sebelumnya")
        print("="*70)

        if last_tested_msg:
            print(f" Status: {last_tested_msg}\n")
            last_tested_msg = ""

        key = get_key_press(" Tekan Tombol [1-9 / A-G / J-M / O / U-W / P / I / T / N / 0]: ").strip().lower()

        if key == "0":
            break
        elif key == "t":
            menu_toggle_steps()
        elif key == "n":
            if os.name == 'nt':
                os.system(f'notepad "{KORDINAT_FILE}"')
            last_tested_msg = "Membuka file koordinat di Notepad..."
        elif key == "i":
            print("\n[>] Menjalankan Alur Lengkap Reset Google Advertising ID (Step 0.1 s/d 0.8)...")
            for sid in ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8"]:
                runner.execute_macro_step(sid, force=True)
            last_tested_msg = "[V] Alur Step 0.1 s/d 0.8 (Reset GAID Lengkap) selesai dieksekusi!"
        elif key == "e":
            print("\n[>] Mengetuk kolom Jumlah pembayaran (916, 1594)...")
            runner.adb.tap(916, 1594, delay_after=1.0)
            last_tested_msg = "[V] Kolom Jumlah pembayaran diketuk."
        elif key == "f":
            print("\n[>] Mengetuk item USDC Morph paling atas (517, 1536)...")
            runner.adb.tap(517, 1536, delay_after=1.0)
            last_tested_msg = "[V] Item USDC Morph diketuk."
        elif key == "g":
            print("\n[>] Mengetuk tombol Konfirmasi Pembayaran (540, 2193)...")
            runner.adb.tap(540, 2193, delay_after=1.0)
            last_tested_msg = "[V] Tombol Konfirmasi Pembayaran diketuk."
        elif key == "p":
            pin_to_type = runner.config.get("pin", "080808")
            print(f"\n[>] Mengetik PIN transaksi {pin_to_type}...")
            coords = runner.config.get("keypad_coords_morph") or runner.config.get("keypad_coords")
            runner.adb.type_pin(pin_to_type, keypad_coords=coords, delay_step=0.3)
            last_tested_msg = f"[V] PIN {pin_to_type} selesai diketik."
        elif key == "d":
            try:
                tuyul_addr = get_last_tuyul_address() or runner.adb.get_clipboard_text()
                if not (tuyul_addr and tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
                    tuyul_addr = input("\n Masukkan Address EVM Tuyul: ").strip()

                print("\n[*] Mendeteksi nominal tagihan USDC dari layar HP...")
                detected = runner.adb.read_required_usdc_from_screen()
                buffer_usdc = float(runner.config.get("usdc_buffer", 0.006))
                if detected:
                    send_amt = round(detected + buffer_usdc, 4)
                    print(f" - Kebutuhan Layar : {detected} USDC")
                    print(f" - Siap Ditransfer  : {send_amt} USDC (Termasuk buffer aman +{buffer_usdc})")
                else:
                    safe_rate = float(runner.config.get("fallback_rate", 17400.0))
                    cur_nom = int(runner.config.get("default_qris_nominal", 18501))
                    base_est = round(cur_nom / safe_rate, 4)
                    send_amt = round(base_est + buffer_usdc, 4)
                    print(f" [!] Nominal layar tidak terdeteksi, estimasi kurs aman: {send_amt} USDC (Buffer +{buffer_usdc})")

                print(f" - Target Tuyul    : {tuyul_addr}")
                print("\n [Y] Eksekusi Transfer Sekarang")
                print(" [N] Batal")
                cf = get_key_press(" Konfirmasi [Y/n]: ").strip().lower()
                if cf != 'n':
                    print(f"\n[*] Mengirim {send_amt} USDC Morph dari Wallet Tebar...")
                    res = runner.wallet.send_usdc(tuyul_addr, send_amt)
                    if res.get("success"):
                        tx = res.get('tx_hash')
                        print(f"\n[V] Sukses Transfer! Tx: {tx}")
                        print(f"    Explorer: {res.get('explorer')}")
                        print("[*] Menunggu 4 detik agar saldo masuk...")
                        time.sleep(4.0)
                        last_tested_msg = f"[V] Saldo {send_amt} USDC Morph terkirim ke Tuyul! Siap tekan Step 9 (Bayar)."
                    else:
                        last_tested_msg = f"[X] Gagal kirim USDC: {res.get('error')}"
                else:
                    last_tested_msg = "Pengiriman dibatalkan."
            except Exception as e:
                last_tested_msg = f"[X] Terjadi kendala saat tebar saldo: {e}"
        elif key in key_mapping:
            target_sid = key_mapping[key]
            target_name = step_map.get(target_sid, {}).get('name', f'Step {target_sid}')
            is_off = step_map.get(target_sid, {}).get('is_off', False)
            if is_off:
                print(f"\n[!] Catatan: Step {target_sid} saat ini berstatus OFF.")
                print(f"[>] Tetap menjalankan Step {target_sid} ({target_name}) untuk pengujian manual...")
                runner.execute_macro_step(target_sid, force=True)
            else:
                print(f"\n[>] Menjalankan Step {target_sid} ({target_name})...")
                runner.execute_macro_step(target_sid)
            last_tested_msg = f"[V] Step {target_sid} ({target_name}) selesai dieksekusi!"
            time.sleep(0.5)
        else:
            last_tested_msg = f"[!] Tombol '{key}' tidak terdaftar."

def restart_terminal():
    print("\n" + "="*70)
    print("      [*] ME-RESTART APLIKASI BOT TERMINAL...")
    print("="*70)
    time.sleep(0.5)
    try:
        import atexit
        atexit.unregister(restore_recorded_screen)
    except Exception:
        pass

    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, script_path] + sys.argv[1:]
    subprocess.call(cmd)
    sys.exit(0)

def main():
    register_auto_restore()
    sync_kordinat_and_config()
    adb = ADBController()

    # Cek argument CLI
    if "--auto" in sys.argv:
        runner = BotRunner()
        runner.run_full_auto()
        sys.exit(0)
    elif "--manual" in sys.argv:
        runner = BotRunner()
        runner.run_manual_mode()
        sys.exit(0)
    elif "--rekam" in sys.argv:
        runner = BotRunner()
        runner.run_rekam_delay()
        sys.exit(0)

    while True:
        cfg = load_config()
        current_clone = cfg.get("clone_app", "dual_space")
        clone_info = CLONE_APPS.get(current_clone, CLONE_APPS["dual_space"])
        devs = adb.get_devices()
        dev_status = f"{devs[0]} (Terhubung)" if devs else "TIDAK ADA PERANGKAT"

        clear_screen()
        print("="*70)
        print("    BOT ADB TERMINAL STANDALONE - BITGET WALLET QRIS MORPH")
        print("="*70)
        print(f" Device Terdeteksi : {dev_status}")
        print(f" Mode Clone Aktif  : {clone_info['name']} ({clone_info['package']})")
        cur_nom = int(cfg.get('default_qris_nominal', 18501))
        nom_display = f"{cur_nom:,}".replace(",", ".")
        print(f" PIN Transaksi     : {cfg.get('pin', '080808')}")
        print(f" Wallet Tebar      : {cfg.get('wallet_tebar', {}).get('address', 'Belum Diatur')}")
        print(f" Nominal Default   : Rp {nom_display}")
        print("="*70)
        print(f" [1] MODE FULL AUTO (Reset -> QRIS {nom_display} -> Tebar -> Bayar PIN -> Claim)")
        print(" [2] MODE MANUAL STEP-BY-STEP (Jalan Per Langkah via ENTER)")
        print(" [3] MODE REKAM DELAY HP (Tekan ENTER Saat Siap, Auto-Simpan ke File)")
        print(" [4] Reset & Buka Clone Saja (Clear Cache + Reset ID Iklan + Mode Pesawat 3s + Launch)")
        print(" [5] Pilih / Ganti Aplikasi Clone (Dual Space / Multiple App / Multi App)")
        print(" [6] Generator GoBiz QRIS & Push ke HP (Uji Coba Gambar QR)")
        print(" [7] Cek Saldo & Test Transfer USDC Morph (Wallet Tebar)")
        print(" [8] Pengelolaan Layar & Resolusi HP (Auto 1080x2400 @ 352 DPI)")
        print(" [9] Kelola / Test Langkah Koordinat Macro (kordinat_qris_morph.txt)")
        print(" [T] Pengaturan ON / OFF Step Koordinat Macro (kordinat_qris_morph.txt)")
        print(" [M] Buka Mirror Layar HP via Scrcpy (Layar Fisik HP Mati)")
        print(" [R] Restart Aplikasi Bot Terminal")
        print(" [0] Kembali / Keluar (Kembalikan Layar Asli HP)")
        print("="*70)

        pilihan = get_key_press(" Masukkan pilihan Anda [0-9 / T / M / R] (Tekan Tombol Langsung): ").strip().lower()

        if pilihan == "1":
            runner = BotRunner()
            ok = runner.run_full_auto()
            if ok or not runner.stopped:
                wait_any_key("\n Tekan sembarang tombol untuk kembali...")
            else:
                time.sleep(0.5)
        elif pilihan == "2":
            runner = BotRunner()
            ok = runner.run_manual_mode()
            if ok or not runner.stopped:
                wait_any_key("\n Tekan sembarang tombol untuk kembali...")
            else:
                time.sleep(0.5)
        elif pilihan == "3":
            runner = BotRunner()
            runner.run_rekam_delay()
            wait_any_key("\n Tekan sembarang tombol untuk kembali...")
        elif pilihan == "4":
            clear_screen()
            adb.reset_and_launch(current_clone, airplane_seconds=cfg.get("airplane_seconds", 3))
            wait_any_key("\n Tekan sembarang tombol untuk kembali...")
        elif pilihan == "5":
            menu_select_clone_app()
        elif pilihan == "6":
            menu_generate_qris()
        elif pilihan == "7":
            menu_wallet_and_token()
        elif pilihan == "8":
            menu_screen_settings()
        elif pilihan == "9":
            menu_manage_steps()
        elif pilihan == "t":
            menu_toggle_steps()
        elif pilihan == "m":
            launch_mirror_screen()
            time.sleep(1.0)
        elif pilihan == "r":
            restart_terminal()
        elif pilihan == "0":
            print("\n[*] Menutup menu bot QRIS Morph...")
            restore_recorded_screen()
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Dibatalkan oleh pengguna (Ctrl+C).")
        restore_recorded_screen()
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[X] TERJADI KENDALA TAK TERDUGA: {e}")
        import traceback
        traceback.print_exc()
        try:
            restore_recorded_screen()
        except Exception:
            pass
        input("\nTekan ENTER untuk keluar...")
        sys.exit(1)
