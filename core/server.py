import os
import sys
import json
import time
import subprocess
import threading
import queue
import re
import socket
import atexit
from collections import deque
from flask import Flask, jsonify, request, Response, send_from_directory

# Path Direktori Proyek
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))
WEB_DIR = os.path.join(CORE_DIR, 'web')
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')
KORDINAT_DIR = os.path.join(CORE_DIR, 'kordinat')
KORDINAT_WD_BARU_FILE = os.path.join(KORDINAT_DIR, 'kordinat_wd_baru.txt')
KORDINAT_WD_OLD_FILE = os.path.join(KORDINAT_DIR, 'kordinat_wd_old.txt')
KORDINAT_CREATE_ACCOUNT_FILE = os.path.join(KORDINAT_DIR, 'kordinat_create_account.txt')
KORDINAT_QRIS_MORPH_FILE = os.path.join(KORDINAT_DIR, 'kordinat_qris_morph.txt')

# Fallback ke CORE_DIR jika file ada di root core
if not os.path.exists(KORDINAT_WD_BARU_FILE) and os.path.exists(os.path.join(CORE_DIR, 'kordinat_wd_baru.txt')):
    KORDINAT_WD_BARU_FILE = os.path.join(CORE_DIR, 'kordinat_wd_baru.txt')
if not os.path.exists(KORDINAT_WD_OLD_FILE) and os.path.exists(os.path.join(CORE_DIR, 'kordinat_wd_old.txt')):
    KORDINAT_WD_OLD_FILE = os.path.join(CORE_DIR, 'kordinat_wd_old.txt')
if not os.path.exists(KORDINAT_CREATE_ACCOUNT_FILE) and os.path.exists(os.path.join(CORE_DIR, 'kordinat_create_account.txt')):
    KORDINAT_CREATE_ACCOUNT_FILE = os.path.join(CORE_DIR, 'kordinat_create_account.txt')
if not os.path.exists(KORDINAT_QRIS_MORPH_FILE) and os.path.exists(os.path.join(CORE_DIR, 'kordinat_qris_morph.txt')):
    KORDINAT_QRIS_MORPH_FILE = os.path.join(CORE_DIR, 'kordinat_qris_morph.txt')
EMAILS_FILE = os.path.join(CORE_DIR, 'emails.txt')

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from screen_manager import (
    record_and_apply_bot_screen,
    restore_recorded_screen,
    read_current_screen,
    get_cached_screen,
    get_connected_devices,
    get_detailed_connected_devices,
    register_auto_restore
)
from menu import (
    get_or_detect_wifi_ip,
    get_usb_device,
    is_port_reachable,
    launch_mirror_screen,
    parse_step_header,
    update_kordinat_txt_step_file,
    update_all_kordinat_txt_steps_file,
    sync_kordinat_and_config
)
from wallet_phrase_helper import get_available_wallet_files, get_phrase_by_index, copy_phrase_to_clipboard
from wd_xlm import update_sleep_in_kordinat

# Setup PATH untuk scrcpy & adb jika di Windows
SCRCPY_DIR = os.path.join(CORE_DIR, "scrcpy-win64-v3.3.4")
if os.path.exists(SCRCPY_DIR) and SCRCPY_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = SCRCPY_DIR + os.pathsep + os.environ.get("PATH", "")

def get_adb_path():
    """Mengembalikan path mutlak adb.exe dari paket terintegrasi scrcpy atau fallback."""
    cand = os.path.join(SCRCPY_DIR, "adb.exe")
    if os.path.exists(cand):
        return cand
    cand2 = os.path.join(CORE_DIR, "platform-tools", "adb.exe")
    if os.path.exists(cand2):
        return cand2
    return "adb"

def get_scrcpy_path():
    """Mengembalikan path mutlak scrcpy.exe."""
    cand = os.path.join(SCRCPY_DIR, "scrcpy.exe")
    if os.path.exists(cand):
        return cand
    return "scrcpy"


# Domain & Cloudflare Tunnel
PUBLIC_DOMAIN = "topnodtools.web.id"
CF_TOKEN_FILE = os.path.join(CORE_DIR, "cloudflare_token.txt")
CF_BIN = os.path.join(CORE_DIR, "bin", "cloudflared.exe")

# Setup Flask Server
app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")

# Port & Binding Configuration
PORT = 2000

def get_local_machine_ip():
    """Mendeteksi IP LAN lokal komputer (misal: 192.168.1.13) secara akurat tanpa 127.0.0.1 / 0.0.0.0."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1" and not ip.startswith("0."):
            return ip
    except Exception:
        pass
    try:
        out = subprocess.run("route print 0.0.0.0", shell=True, capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                candidate = parts[3]
                if candidate.startswith("192.168.") or candidate.startswith("10.") or candidate.startswith("172."):
                    return candidate
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and ip != "127.0.0.1":
            return ip
    except Exception:
        pass
    return "192.168.1.13"

HOST = get_local_machine_ip()

# Cloudflare Tunnel Process Management
cf_tunnel_proc = None
cf_tunnel_lock = threading.Lock()

def cleanup_project_cloudflared():
    """Menghentikan proses cloudflared.exe lama dari folder proyek ini agar tidak bertumpuk."""
    target_bin = os.path.normpath(CF_BIN).lower()
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if p.info['name'] and 'cloudflared' in p.info['name'].lower():
                    exe_path = os.path.normpath(p.info.get('exe') or '').lower()
                    if exe_path == target_bin:
                        p.terminate()
            except Exception:
                pass
    except Exception:
        pass

def start_cloudflare_tunnel(local_ip=None, port=PORT):
    """Menjalankan Cloudflare Tunnel untuk domain topnodtools.web.id di latar belakang."""
    global cf_tunnel_proc
    token_path = CF_TOKEN_FILE if os.path.exists(CF_TOKEN_FILE) else os.path.join(PROJECT_ROOT, "cloudflare_token.txt")
    bin_path = CF_BIN if os.path.exists(CF_BIN) else "cloudflared"

    if not os.path.exists(token_path):
        broadcast_log("[TUNNEL WARNING] File cloudflare_token.txt tidak ditemukan.")
        return False
        
    try:
        with open(token_path, 'r', encoding='utf-8') as f:
            token = f.read().strip()
        if not token:
            return False
            
        target_ip = local_ip or get_local_machine_ip()
        local_url = f"http://{target_ip}:{port}"
        
        with cf_tunnel_lock:
            if cf_tunnel_proc and cf_tunnel_proc.poll() is None:
                return True
                
            cleanup_project_cloudflared()
            time.sleep(0.3)
            cmd = [bin_path, "tunnel", "run", "--url", local_url, "--token", token]
            cf_tunnel_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            broadcast_log(f"[TUNNEL] Cloudflare Tunnel aktif: https://{PUBLIC_DOMAIN} -> {local_url}")
            return True
    except Exception as e:
        broadcast_log(f"[TUNNEL ERROR] Gagal memulai Cloudflare Tunnel: {e}")
        return False

def stop_cloudflare_tunnel():
    """Menghentikan Cloudflare Tunnel saat server dimatikan."""
    global cf_tunnel_proc
    with cf_tunnel_lock:
        if cf_tunnel_proc and cf_tunnel_proc.poll() is None:
            try:
                cf_tunnel_proc.terminate()
                cf_tunnel_proc.wait(timeout=2)
            except Exception:
                cf_tunnel_proc.kill()
            cf_tunnel_proc = None
            broadcast_log("[TUNNEL] Cloudflare Tunnel dinonaktifkan.")
        cleanup_project_cloudflared()

def get_unique_physical_devices():
    """Mengembalikan daftar unik perangkat fisik (prioritas USB dibanding Wi-Fi jika serial sama)."""
    devs = get_detailed_connected_devices()
    unique = {}
    for d in devs:
        k = d.get("model") or d["serial"]
        if k not in unique or (not d["is_wifi"] and unique[k]["is_wifi"]):
            unique[k] = d
    return list(unique.values())

# Multi-Device State: keyed by device serial
device_bots = {}
device_wallet_files = {}
process_lock = threading.Lock()

# Screen Off & Mirror Process Management
screen_off_procs = {}
screen_off_lock = threading.Lock()
mirror_procs = {}
mirror_lock = threading.Lock()

def stop_scrcpy_for_serial(serial):
    """Menghentikan proses scrcpy aktif untuk serial tertentu agar tidak duplikat/bentrok."""
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['name'] and 'scrcpy' in p.info['name'].lower():
                    cmd = " ".join(p.info['cmdline'] or [])
                    if f"-s {serial}" in cmd or f"--serial={serial}" in cmd or f"-s {serial}:5555" in cmd:
                        p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass

def launch_scrcpy_mirror(serial, model=None, fps=120):
    """
    Meluncurkan window SCRCPY GUI di desktop Windows secara mandiri, interaktif,
    dan TANPA jendela CMD hitam (no blink, no adb stack).
    Menggunakan launcher resmi WScript.Shell.Run(..., 0, false) yang menyembunyikan console
    namun menampilkan window GUI SDL2 Direct3D secara murni di desktop.
    """
    global screen_off_procs
    scrcpy_path = get_scrcpy_path()
    if not os.path.exists(scrcpy_path):
        return False, "File scrcpy.exe tidak ditemukan di folder scrcpy-win64-v3.3.4"

    scrcpy_dir = os.path.dirname(scrcpy_path)
    dev_name = model or serial

    # 1. Hentikan scrcpy headless screen-off jika sedang aktif untuk serial ini agar MediaCodec encoder tidak bentrok
    with screen_off_lock:
        if serial in screen_off_procs:
            p = screen_off_procs[serial]
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
            screen_off_procs.pop(serial, None)

    # 2. Hentikan proses scrcpy mirror yang sudah berjalan sebelumnya untuk serial ini
    stop_scrcpy_for_serial(serial)
    time.sleep(0.3)

    title = f"MIRROR {dev_name} ({serial}) [{fps} FPS]"
    flags = f'-s {serial} --window-title="{title}" -S -w --max-fps={fps} --video-buffer=0 --video-bit-rate=16M --no-audio'

    try:
        if os.name == 'nt':
            try:
                import win32com.client
                wscript = win32com.client.Dispatch("WScript.Shell")
                wscript.CurrentDirectory = scrcpy_dir
                cmd = f'cmd /c ""{scrcpy_path}" {flags}"'
                wscript.Run(cmd, 0, False)
            except Exception:
                # Fallback ke wscript scrcpy-noconsole.vbs
                vbs_path = os.path.join(scrcpy_dir, "scrcpy-noconsole.vbs")
                if os.path.exists(vbs_path):
                    import shlex
                    subprocess.Popen(
                        ["wscript", vbs_path] + shlex.split(flags),
                        cwd=scrcpy_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    import shlex
                    subprocess.Popen(
                        [scrcpy_path] + shlex.split(flags),
                        cwd=scrcpy_dir,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
        else:
            import shlex
            subprocess.Popen(
                [scrcpy_path] + shlex.split(flags),
                cwd=scrcpy_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        broadcast_log(f"[{dev_name}] [MIRROR] SCRCPY aktif ({fps} FPS) di desktop tanpa blink CMD.", device=serial)
        return True, f"SCRCPY ({fps} FPS) untuk {dev_name} berhasil diluncurkan!"
    except Exception as e:
        return False, f"Gagal meluncurkan SCRCPY: {e}"

def set_screen_off_mode(serial, enabled=True):
    """Mengaktifkan/menonaktifkan mode layar mati (screen off) untuk perangkat tertentu."""
    global screen_off_procs, mirror_procs
    scrcpy_path = get_scrcpy_path()
    adb_path = get_adb_path()
        
    dev_name = serial
    for d in get_detailed_connected_devices():
        if d["serial"] == serial:
            dev_name = d.get("model") or serial
            break

    with screen_off_lock:
        if enabled:
            # Tutup scrcpy mirror window jika aktif agar encoder MediaCodec tidak bentrok
            with mirror_lock:
                if serial in mirror_procs:
                    p = mirror_procs[serial]
                    if p and p.poll() is None:
                        try:
                            p.terminate()
                        except Exception:
                            pass
                    mirror_procs.pop(serial, None)

            if serial in screen_off_procs and screen_off_procs[serial].poll() is None:
                return True, "Mode Screen Off sudah aktif"
                
            subprocess.run([adb_path, "-s", serial, "shell", "svc", "power", "stayon", "usb"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=5)
            cmd = [scrcpy_path, "-s", serial, "-S", "-w", "--no-window", "--no-audio"]
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=os.path.dirname(scrcpy_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                screen_off_procs[serial] = proc
                broadcast_log(f"[{dev_name}] [SCREEN OFF] Layar fisik dimatikan. Bot tetap aktif di latar belakang.", device=serial)
                return True, "Mode Screen Off Aktif"
            except Exception as e:
                return False, f"Gagal mengaktifkan Screen Off: {e}"
        else:
            if serial in screen_off_procs:
                p = screen_off_procs[serial]
                if p and p.poll() is None:
                    try:
                        p.terminate()
                        p.wait(timeout=2)
                    except Exception:
                        p.kill()
                del screen_off_procs[serial]
                
            subprocess.run([adb_path, "-s", serial, "shell", "svc", "power", "stayon", "false"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=5)
            subprocess.run([adb_path, "-s", serial, "shell", "input", "keyevent", "224"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=5)
            broadcast_log(f"[{dev_name}] [SCREEN ON] Layar fisik dinyalakan kembali.", device=serial)
            return True, "Mode Screen On (Layar Nyala)"

def execute_step_commands(serial, step, mode='create_account', account_num=1):
    """Mengeksekusi seluruh baris perintah dalam satu langkah macro secara manual via ADB."""
    config = load_config_data()
    pin = config.get("pin", "080808")
    ref_code = config.get("current_referral_code") or config.get("master_referral_code", "srTwuLUy")
    alamat_wd = config.get("alamat_wd", "")
    if mode in ("qris_morph", "morph", "qm", "qris"):
        keypad_coords = config.get("keypad_coords_morph") or config.get("keypad_coords", {})
    else:
        keypad_coords = config.get("keypad_coords", {})
    slot_coords = config.get("clone_slot_coords", {})
    adb_path = get_adb_path()

    dev_name = serial
    for d in get_detailed_connected_devices():
        if d["serial"] == serial:
            dev_name = d.get("model") or serial
            break

    broadcast_log(f"[{dev_name}] [MANUAL STEP] Memulai Step {step['id']}: {step['name']}...", device=serial)

    def run_adb(shell_cmd):
        cmd = [adb_path, "-s", serial, "shell"] + shell_cmd.split()
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (res.stdout or "").strip()

    wallet_file = device_wallet_files.get(serial) or config.get("active_wallet_file")
    p_data = get_phrase_by_index(account_num, wallet_file)
    phrase_val = p_data.get("phrase", "") if p_data else ""

    commands = step.get("commands", [])
    for cmd in commands:
        cmd_stripped = cmd.strip()
        if not cmd_stripped or cmd_stripped.startswith('#'):
            continue

        # Ganti semua placeholder template dinamis
        cmd_stripped = (cmd_stripped
                        .replace("{ALAMAT_WD}", str(alamat_wd))
                        .replace("{ACCOUNT_NUM}", str(account_num))
                        .replace("{PIN}", str(pin))
                        .replace("{REFERRAL_CODE}", str(ref_code))
                        .replace("{PHRASE}", str(phrase_val)))
        cmd_lower = cmd_stripped.lower()

        if cmd_lower in ("input phrase_copy", "phrase_copy"):
            if phrase_val:
                copy_phrase_to_clipboard(phrase_val)
                broadcast_log(f"[{dev_name}] [PHRASE COPY] Frasa #{account_num} disalin ke clipboard PC: {phrase_val}", device=serial)
            else:
                broadcast_log(f"[{dev_name}] [PHRASE WARNING] Frasa #{account_num} tidak ditemukan di {wallet_file or 'file wallet'}", device=serial)

        elif cmd_lower in ("input phrase_paste", "phrase_paste"):
            run_adb("input keyevent 279")
            broadcast_log(f"[{dev_name}] [PHRASE PASTE] Tempel frasa via Keyevent 279", device=serial)

        elif cmd_lower in ("input phrase_type", "phrase_type"):
            if phrase_val:
                escaped = phrase_val.replace(" ", "%s")
                run_adb(f"input text '{escaped}'")
                broadcast_log(f"[{dev_name}] [PHRASE TYPE] Frasa #{account_num} berhasil diketik via ADB", device=serial)
            else:
                broadcast_log(f"[{dev_name}] [PHRASE WARNING] Frasa #{account_num} kosong, tidak dapat mengetik", device=serial)

        elif cmd_lower in ("input step2_open_wallet", "step2_open_wallet"):
            cfg = load_config_data()
            s2_mode = cfg.get("step2_mode", "dompet")
            if s2_mode == "profil":
                run_adb("input tap 78 119")
                broadcast_log(f"[{dev_name}] [STEP 2] Tap Profil Avatar (78, 119)", device=serial)
            else:
                run_adb("input tap 197 284")
                broadcast_log(f"[{dev_name}] [STEP 2] Tap Dompet Saya (197, 284)", device=serial)

        elif cmd_lower.startswith("sleep"):
            parts = cmd_stripped.split()
            if len(parts) >= 2:
                try:
                    time.sleep(float(parts[1]))
                except ValueError:
                    pass

        elif cmd_lower.startswith("input slot_tap"):
            slot_idx = str(((account_num - 1) % 7) + 1)
            coord = slot_coords.get(slot_idx, {"x": 225, "y": 391})
            run_adb(f"input tap {coord['x']} {coord['y']}")
            broadcast_log(f"[{dev_name}] Tap Slot #{slot_idx} ({coord['x']}, {coord['y']})", device=serial)

        elif cmd_lower.startswith("input type_kyc_email"):
            emails = []
            if os.path.exists(EMAILS_FILE):
                with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
                    emails = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            email_val = emails[(account_num - 1) % len(emails)] if emails else "test@gmail.com"
            run_adb(f"input text {email_val}")
            run_adb("input keyevent 111")
            run_adb("input keyevent 4")
            broadcast_log(f"[{dev_name}] Type KYC Email: {email_val}", device=serial)

        elif cmd_lower.startswith("input imap_fetch_and_type_otp"):
            broadcast_log(f"[{dev_name}] [IMAP] Mengambil 6-digit OTP dari inbox...", device=serial)
            try:
                from imap_helper import fetch_bitget_otp
                emails = []
                if os.path.exists(EMAILS_FILE):
                    with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
                        emails = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                if emails:
                    email_line = emails[(account_num - 1) % len(emails)]
                    parts = [p.strip() for p in email_line.split('|')] if '|' in email_line else [email_line, '']
                    user_email = parts[0]
                    pass_email = parts[1] if len(parts) > 1 else ""
                    otp = fetch_bitget_otp(
                        email_user=user_email,
                        email_pass=pass_email,
                        imap_server=config.get("imap_default_server", "imap.gmail.com"),
                        imap_port=config.get("imap_default_port", 993),
                        use_ssl=config.get("imap_use_ssl", True),
                        min_timestamp=time.time() - 120,
                        timeout=30
                    )
                    if otp:
                        broadcast_log(f"[{dev_name}] [IMAP SUCCESS] OTP: {otp}", device=serial)
                        run_adb("input tap 868 315")
                        for ch in str(otp):
                            if ch.isdigit():
                                run_adb(f"input keyevent {7 + int(ch)}")
                                time.sleep(0.08)
                        run_adb(f"input text {otp}")
                    else:
                        broadcast_log(f"[{dev_name}] [IMAP WARNING] OTP belum ditemukan", device=serial)
            except Exception as ex:
                broadcast_log(f"[{dev_name}] [IMAP ERROR] {ex}", device=serial)

        elif cmd_lower.startswith("input copy_own_referral"):
            run_adb("input keyevent 279")
            time.sleep(0.5)
            clip_res = run_adb("cmd clipboard get")
            if clip_res and len(clip_res) < 30 and re.match(r'^[A-Za-z0-9]+$', clip_res):
                cfg = load_config_data()
                cfg["current_referral_code"] = clip_res
                cfg["referral_code"] = clip_res
                save_config_data(cfg)
                broadcast_log(f"[{dev_name}] [REFERRAL] Disalin: {clip_res}", device=serial)
            else:
                broadcast_log(f"[{dev_name}] Copy Own Referral", device=serial)

        elif cmd_lower.startswith("input tap_rel"):
            parts = cmd_stripped.split()
            if len(parts) >= 4:
                rx, ry = float(parts[2]), float(parts[3])
                x_px = int(rx * 1080)
                y_px = int(ry * 2400)
                run_adb(f"input tap {x_px} {y_px}")
                broadcast_log(f"[{dev_name}] Tap Rel ({rx:.2f}, {ry:.2f}) -> ({x_px}, {y_px})", device=serial)

        elif cmd_lower.startswith("input tap") and not cmd_lower.startswith("input tap_rel"):
            parts = cmd_stripped.split()
            if len(parts) >= 4:
                x, y = int(parts[2]), int(parts[3])
                run_adb(f"input tap {x} {y}")
                broadcast_log(f"[{dev_name}] Tap ({x}, {y})", device=serial)

        elif cmd_lower.startswith("input swipe"):
            parts = cmd_stripped.split()
            if len(parts) >= 6:
                x1, y1, x2, y2 = parts[2], parts[3], parts[4], parts[5]
                dur = parts[6] if len(parts) >= 7 else "500"
                run_adb(f"input swipe {x1} {y1} {x2} {y2} {dur}")
                broadcast_log(f"[{dev_name}] Swipe ({x1},{y1}) -> ({x2},{y2})", device=serial)

        elif cmd_lower.startswith("input text"):
            text_val = cmd_stripped[len("input text"):].strip()
            text_val = (text_val
                        .replace("{ALAMAT_WD}", str(alamat_wd))
                        .replace("{ACCOUNT_NUM}", str(account_num))
                        .replace("{PIN}", str(pin))
                        .replace("{REFERRAL_CODE}", str(ref_code))
                        .replace("{PHRASE}", str(phrase_val)))
            if not text_val:
                broadcast_log(f"[{dev_name}] [WARNING] Input text kosong! Periksa alamat_wd / data config.", device=serial)
            else:
                run_adb(f"input text {text_val}")
                broadcast_log(f"[{dev_name}] Type text: {text_val}", device=serial)

        elif cmd_lower.startswith("input keyevent"):
            parts = cmd_stripped.split()
            if len(parts) >= 3:
                kc = parts[2]
                if kc.lower() in ("back", "4"):
                    kc = "4"
                    broadcast_log(f"[{dev_name}] Keyevent 4 (Tutup Keyboard)", device=serial)
                else:
                    broadcast_log(f"[{dev_name}] Keyevent {kc}", device=serial)
                run_adb(f"input keyevent {kc}")

        elif cmd_lower.startswith("pin"):
            def_keypad = {
                "1": (205, 1550), "2": (540, 1550), "3": (875, 1550),
                "4": (205, 1720), "5": (540, 1720), "6": (875, 1720),
                "7": (205, 1890), "8": (540, 1890), "9": (875, 1890),
                "0": (540, 2060)
            }
            if mode in ("qris_morph", "morph", "qm", "qris"):
                coords = config.get("keypad_coords_morph") or def_keypad
            else:
                coords = keypad_coords or def_keypad
            for digit in str(pin):
                if digit in coords:
                    c = coords[digit]
                    if isinstance(c, dict):
                        kx = c.get('x')
                        ky = c.get('y')
                    elif isinstance(c, (list, tuple)) and len(c) >= 2:
                        kx, ky = c[0], c[1]
                    else:
                        kx, ky = None, None
                    if kx is not None and ky is not None:
                        run_adb(f"input tap {kx} {ky}")
                        time.sleep(0.12)
            broadcast_log(f"[{dev_name}] PIN keypad entered", device=serial)

        elif cmd_lower.startswith("monkey"):
            cmd_body = cmd_stripped[len("monkey"):].strip()
            run_adb(f"monkey {cmd_body}")
            broadcast_log(f"[{dev_name}] Monkey {cmd_body}", device=serial)

        else:
            run_adb(cmd_stripped)
            broadcast_log(f"[{dev_name}] Exec: {cmd_stripped}", device=serial)

        time.sleep(0.1)

    broadcast_log(f"[{dev_name}] [MANUAL STEP] Step {step['id']} Selesai Dieksekusi.", device=serial)

# Logging & SSE Broadcast (Memory-Capped for 4GB RAM Host)
log_history = deque(maxlen=300)
log_lock = threading.Lock()
subscribers = []
subscribers_lock = threading.Lock()

def broadcast_log(line, device=None):
    """Menyimpan line log dan mengirim ke semua klien SSE yang terhubung."""
    clean_line = line.rstrip("\r\n")
    if not clean_line:
        return
    item = {"line": clean_line, "device": device, "time": time.time()}
    with log_lock:
        log_history.append(item)
    with subscribers_lock:
        dead_subs = []
        for q in list(subscribers):
            try:
                q.put_nowait(item)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(item)
                except Exception:
                    pass
            except Exception:
                dead_subs.append(q)
        for dq in dead_subs:
            if dq in subscribers:
                subscribers.remove(dq)

def read_device_process_output(serial, model, proc):
    """Thread pembaca output stdout dari subprocess bot per device."""
    global device_bots
    dev_tag = f"[{model or serial}]"
    
    mode = device_bots.get(serial, {}).get("mode", "bot")
    broadcast_log(f"{dev_tag} [SYSTEM] Subprocess bot ({mode}) dimulai pada perangkat {serial}.", device=serial)
    
    for raw_line in iter(proc.stdout.readline, ''):
        line = raw_line.rstrip("\r\n")
        if not line and proc.poll() is not None:
            break
        
        broadcast_log(f"{dev_tag} {line}", device=serial)
        
        # Deteksi nomor akun yang sedang diproses
        m_start = re.search(r"MEMPROSES\s+(?:AKUN\s+)?CLONE\s+BITGET\s+KE-(\d+)", line, re.IGNORECASE)
        if not m_start:
            m_start = re.search(r"MEMPROSES\s+AKUN\s+CLONE\s+KE-(\d+)", line, re.IGNORECASE)
            
        if m_start and m_start.group(1):
            clone_num = int(m_start.group(1))
            with process_lock:
                if serial in device_bots:
                    device_bots[serial]["current_clone"] = clone_num
                    device_bots[serial]["next_clone"] = clone_num + 1
                    device_bots[serial]["state"] = "RUNNING"
            
        # Deteksi kode referral yang disalin & update config otomatis
        m_ref = re.search(r"\[REFERRAL\]\s+Kode\s+referral\s+berhasil\s+disalin:\s*([A-Za-z0-9]+)", line, re.IGNORECASE)
        if m_ref:
            new_ref = m_ref.group(1).strip()
            cfg = load_config_data()
            cfg["current_referral_code"] = new_ref
            cfg["referral_code"] = new_ref
            save_config_data(cfg)
            broadcast_log(f"{dev_tag} [SYNC] Kode referral aktif diperbarui ke config: {new_ref}", device=serial)

        # Deteksi status akun selesai dan menunggu konfirmasi akun berikutnya
        if "lanjut loop WD clone berikutnya" in line or \
           "lanjut ke pembuatan akun clone berikutnya" in line or \
           "[STEP-BY-STEP] Menunggu konfirmasi..." in line or \
           "Siap di beranda Bitget?" in line or \
           "Tekan ENTER untuk lanjut" in line or \
           "[REKAM DELAY] Tekan ENTER" in line:
            m_next = re.search(r"ke-(\d+)", line, re.IGNORECASE)
            next_num = int(m_next.group(1)) if m_next else None
            with process_lock:
                if serial in device_bots:
                    if next_num:
                        device_bots[serial]["next_clone"] = next_num
                    device_bots[serial]["state"] = "WAITING_NEXT"
            prompt_label = f"Siap lanjut ke Clone ke-{next_num}." if next_num else "Menunggu konfirmasi di layar HP."
            broadcast_log(f"{dev_tag} [PROMPT] {prompt_label} Tekan Lanjut (ENTER / CTRL+V).", device=serial)
            
        elif ("AKUN CLONE KE-" in line or "CLONE KE-" in line) and "BERHASIL SELESAI DIPROSES" in line:
            with process_lock:
                if serial in device_bots:
                    device_bots[serial]["state"] = "WAITING_NEXT"

        elif "PROGRAM DIPAUSE" in line:
            with process_lock:
                if serial in device_bots:
                    device_bots[serial]["state"] = "WAITING_NEXT"
            broadcast_log(f"{dev_tag} [PROMPT] Bot DIPAUSE. Tekan ENTER/CTRL+V untuk lanjut, atau 'Q' untuk stop.", device=serial)

    proc.stdout.close()
    proc.wait()
    
    with process_lock:
        if serial in device_bots:
            device_bots[serial]["process"] = None
            device_bots[serial]["state"] = "IDLE"
            device_bots[serial]["mode"] = None
        
    broadcast_log(f"{dev_tag} [SYSTEM] Subprocess bot telah selesai (Exit Code: {proc.returncode}).", device=serial)

def load_config_data():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config_data(data):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        return False

def count_available_emails():
    """Menghitung total baris email aktif di core/emails.txt."""
    if not os.path.exists(EMAILS_FILE):
        return 0
    try:
        with open(EMAILS_FILE, 'r', encoding='utf-8') as f:
            valid_emails = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            return len(valid_emails)
    except Exception:
        return 0

def get_kordinat_file_by_mode(mode_or_type):
    """Mendapatkan file path koordinat master berdasarkan mode operasi."""
    if not mode_or_type:
        return KORDINAT_WD_BARU_FILE
    m = str(mode_or_type).lower().strip()
    if m in ('create_account', 'account', 'ca', 'buat_akun'):
        return KORDINAT_CREATE_ACCOUNT_FILE
    elif m in ('qris_morph', 'morph', 'qm', 'qris'):
        return KORDINAT_QRIS_MORPH_FILE
    elif m in ('wd_baru', 'baru', 'wd_xlm', 'wd'):
        return KORDINAT_WD_BARU_FILE
    elif m in ('wd_old', 'old'):
        return KORDINAT_WD_OLD_FILE
    else:
        return KORDINAT_WD_BARU_FILE

def parse_steps_from_file(filepath, disabled_list=None):
    """Membaca file koordinat txt dan mengembalikan list objek step terstruktur."""
    if disabled_list is None:
        disabled_list = []
    disabled_str = [str(x) for x in disabled_list]
    steps = []
    if os.path.exists(filepath):
        current_step = None
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                header = parse_step_header(stripped)
                if header:
                    step_id = header['id']
                    is_disabled = header['is_off'] or (str(step_id) in disabled_str)
                    current_step = {
                        "id": step_id,
                        "name": header['name'],
                        "full_title": header['full_title'],
                        "is_off": is_disabled,
                        "enabled": not is_disabled,
                        "commands": [],
                        "sleep": None
                    }
                    steps.append(current_step)
                    continue
                if stripped.startswith('#') or stripped.startswith('---'):
                    continue
                if current_step is not None:
                    current_step['commands'].append(stripped)
                    parts = stripped.split()
                    if parts and parts[0].lower() == 'sleep' and len(parts) > 1:
                        try:
                            current_step['sleep'] = float(parts[1])
                        except ValueError:
                            pass
    return steps

def start_single_device_bot(serial, model, options):
    """Menjalankan bot pada satu target perangkat serial secara spesifik."""
    global device_bots
    
    with process_lock:
        if serial in device_bots and device_bots[serial].get("process") is not None:
            proc = device_bots[serial]["process"]
            if proc.poll() is None:
                return {"status": "error", "message": f"Perangkat {model} ({serial}) sedang menjalankan bot!"}
                
        bot_mode = options.get("mode", "wd_xlm")
        start_index = options.get("start_index")
        manual_mode = options.get("manual", False)
        rekam_mode = options.get("rekam", False)
        master_referral = options.get("master_referral")
        
        config = load_config_data()
        if start_index is not None:
            try:
                config["start_index"] = int(start_index)
            except ValueError:
                pass
                
        if master_referral:
            clean_ref = str(master_referral).strip()
            config["master_referral_code"] = clean_ref
            config["current_referral_code"] = clean_ref
            config["referral_code"] = clean_ref

        alamat_wd = options.get("alamat_wd")
        if alamat_wd:
            config["alamat_wd"] = str(alamat_wd).strip()

        save_config_data(config)
        start_idx = config.get("start_index", 1)
        
        # Format resolusi layar bot spesifik ke device ini
        record_and_apply_bot_screen(serial=serial, silent=True)
        
        wallet_file = options.get("wallet_file") or device_wallet_files.get(serial) or config.get("active_wallet_file")
        if wallet_file:
            device_wallet_files[serial] = wallet_file

        if bot_mode == "create_account":
            script_file = "create_account.py"
        elif bot_mode == "qris_morph":
            script_file = "qris_morph.py"
        else:
            script_file = "wd_xlm.py"
            
        cmd = [sys.executable, "-u", os.path.join(CORE_DIR, script_file), "--device", serial]
        if bot_mode in ("wd_old", "old") and script_file == "wd_xlm.py":
            cmd.append("--old")
        if wallet_file and script_file == "wd_xlm.py":
            cmd.extend(["--wallet-file", wallet_file])
        if manual_mode:
            cmd.append("--manual")
        elif rekam_mode:
            cmd.append("--rekam")
        else:
            if bot_mode == "qris_morph":
                cmd.append("--auto")
            
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["BOT_MANAGED_SCREEN"] = "1"
        env["ANDROID_SERIAL"] = serial
        
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=PROJECT_ROOT,
                env=env
            )
            device_bots[serial] = {
                "process": proc,
                "state": "RUNNING",
                "mode": bot_mode,
                "current_clone": start_idx,
                "next_clone": start_idx + 1,
                "model": model,
                "serial": serial,
                "wallet_file": wallet_file
            }
        except Exception as e:
            return {"status": "error", "message": f"Gagal menjalankan bot pada {serial}: {e}"}
            
        t = threading.Thread(target=read_device_process_output, args=(serial, model, proc), daemon=True)
        t.start()
        
    return {
        "status": "success",
        "message": f"Bot {bot_mode} dimulai pada {model} ({serial}) [Clone #{start_idx}]",
        "serial": serial,
        "model": model,
        "bot_state": "RUNNING",
        "current_clone": start_idx
    }

def stop_single_device_bot(serial):
    """Menghentikan bot pada perangkat tertentu secara aman."""
    global device_bots
    with process_lock:
        if serial not in device_bots or device_bots[serial].get("process") is None:
            if serial in device_bots:
                device_bots[serial]["state"] = "IDLE"
            return True
        
        proc = device_bots[serial]["process"]
        try:
            proc.stdin.write("q\n")
            proc.stdin.flush()
        except Exception:
            pass
            
        time.sleep(0.4)
        if proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.4)
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
                
        device_bots[serial]["process"] = None
        device_bots[serial]["state"] = "IDLE"
        device_bots[serial]["mode"] = None
    return True

# ==============================================================================
# ROUTE STATIC FILE (UI DASHBOARD)
# ==============================================================================

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/')
def serve_index():
    return send_from_directory(WEB_DIR, 'index.html', max_age=0)

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(WEB_DIR, path, max_age=0)

# ==============================================================================
# API ENDPOINTS STATUS & MULTI-DEVICE
# ==============================================================================

@app.route('/api/status', methods=['GET'])
def api_status():
    detailed_devs = get_detailed_connected_devices()
    unique_devs = get_unique_physical_devices()
    config = load_config_data()
    screen_off_serials = [s for s, p in screen_off_procs.items() if p.poll() is None]
    available_wallets = get_available_wallet_files()
    def_wallet = config.get("active_wallet_file", available_wallets[0] if available_wallets else "")
    
    # Augment setiap device dengan status bot-nya, screen off & wallet file
    for d in detailed_devs:
        s = d["serial"]
        bot = device_bots.get(s, {})
        d["bot_state"] = bot.get("state", "IDLE")
        d["active_mode"] = bot.get("mode")
        d["current_clone"] = bot.get("current_clone")
        d["next_clone"] = bot.get("next_clone")
        d["is_screen_off"] = (s in screen_off_serials)
        d["wallet_file"] = device_wallet_files.get(s, def_wallet)

    for d in unique_devs:
        s = d["serial"]
        bot = device_bots.get(s, {})
        d["bot_state"] = bot.get("state", "IDLE")
        d["active_mode"] = bot.get("mode")
        d["current_clone"] = bot.get("current_clone")
        d["next_clone"] = bot.get("next_clone")
        d["is_screen_off"] = (s in screen_off_serials)
        d["wallet_file"] = device_wallet_files.get(s, def_wallet)
        
    any_running = any(b.get("state") in ("RUNNING", "WAITING_NEXT") for b in device_bots.values())
    all_screen_off = len(unique_devs) > 0 and all(d.get("is_screen_off") for d in unique_devs)
    
    # Target device aktif yang dipilih oleh client (atau default pertama)
    selected_serial = request.args.get("device")
    if not selected_serial:
        selected_serial = config.get("target_device")
    if not selected_serial or not any(d["serial"] == selected_serial for d in detailed_devs):
        if detailed_devs:
            selected_serial = detailed_devs[0]["serial"]
        else:
            selected_serial = None

    active_bot = device_bots.get(selected_serial, {})
    screen_info = read_current_screen(serial=selected_serial)
    cached_res = get_cached_screen(serial=selected_serial)
    cached_size = cached_res[0] if cached_res else None
    cached_density = cached_res[1] if cached_res and len(cached_res) > 1 else None
    cached_font = cached_res[2] if cached_res and len(cached_res) > 2 else None
    
    usb_dev = next((d["serial"] for d in detailed_devs if not d["is_wifi"]), None)
    wifi_ip = next((d["serial"].split(":")[0] for d in detailed_devs if d["is_wifi"]), None)
    
    return jsonify({
        "status": "success",
        "devices": detailed_devs,
        "unique_devices": unique_devs,
        "active_device": selected_serial,
        "any_running": any_running,
        "screen_off_devices": screen_off_serials,
        "screen_off_all": all_screen_off,
        "bot_state": active_bot.get("state", "IDLE"),
        "active_mode": active_bot.get("mode"),
        "current_clone": active_bot.get("current_clone"),
        "next_clone": active_bot.get("next_clone"),
        "usb_device": usb_dev,
        "wifi_ip": wifi_ip,
        "server_port": PORT,
        "local_machine_ip": get_local_machine_ip(),
        "wallets": available_wallets,
        "device_wallets": device_wallet_files,
        "screen": {
            "active_size": screen_info.get("active_size"),
            "active_density": screen_info.get("active_density"),
            "physical_size": screen_info.get("physical_size"),
            "physical_density": screen_info.get("physical_density"),
            "cached_size": cached_size,
            "cached_density": cached_density,
            "is_bot_format": (screen_info.get("active_size") == "1080x2400" and screen_info.get("active_density") == "352")
        },
        "referral": {
            "current_code": config.get("current_referral_code") or config.get("master_referral_code") or "srTwuLUy",
            "master_code": config.get("master_referral_code") or "srTwuLUy"
        },
        "emails": {
            "total_available": count_available_emails()
        },
        "tunnel": {
            "domain": PUBLIC_DOMAIN,
            "public_url": f"https://{PUBLIC_DOMAIN}",
            "is_online": (cf_tunnel_proc is not None and cf_tunnel_proc.poll() is None)
        },
        "config": config
    })

@app.route('/api/devices', methods=['GET'])
def api_devices():
    devs = get_detailed_connected_devices()
    screen_off_serials = [s for s, p in screen_off_procs.items() if p.poll() is None]
    available_wallets = get_available_wallet_files()
    def_wallet = load_config_data().get("active_wallet_file", available_wallets[0] if available_wallets else "")
    for d in devs:
        s = d["serial"]
        bot = device_bots.get(s, {})
        d["bot_state"] = bot.get("state", "IDLE")
        d["active_mode"] = bot.get("mode")
        d["current_clone"] = bot.get("current_clone")
        d["next_clone"] = bot.get("next_clone")
        d["is_screen_off"] = (s in screen_off_serials)
        d["wallet_file"] = device_wallet_files.get(s, def_wallet)
    return jsonify({
        "status": "success",
        "devices": devs,
        "count": len(devs),
        "unique_devices": get_unique_physical_devices(),
        "wallets": available_wallets
    })

# ==============================================================================
# API BOT KONTROL MULTI-DEVICE
# ==============================================================================

@app.route('/api/bot/start', methods=['POST'])
def api_bot_start():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    detailed_devs = get_detailed_connected_devices()
    
    if not detailed_devs:
        return jsonify({"status": "error", "message": "Tidak ada perangkat Android terdeteksi via ADB!"}), 400

    # Mode: Jalankan di semua perangkat fisik sekaligus
    if target == "all":
        results = []
        for dev in get_unique_physical_devices():
            r = start_single_device_bot(dev["serial"], dev["model"], data)
            results.append(r)
        return jsonify({
            "status": "success",
            "message": f"Menjalankan bot pada {len(results)} perangkat fisik sekaligus",
            "results": results
        })

    # Mode: Jalankan pada device spesifik
    serial = target or detailed_devs[0]["serial"]
    model = next((d["model"] for d in detailed_devs if d["serial"] == serial), "Android")
    res = start_single_device_bot(serial, model, data)
    status_code = 200 if res["status"] == "success" else 400
    return jsonify(res), status_code

@app.route('/api/bot/next', methods=['POST'])
def api_bot_next():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    custom_num = data.get("account_num")
    input_str = f"{custom_num}\n" if custom_num else "\n"
    
    targets = [target] if target and target != "all" else list(device_bots.keys())
    sent_count = 0
    
    for s in targets:
        bot = device_bots.get(s)
        if bot and bot.get("process") and bot["process"].poll() is None:
            try:
                bot["process"].stdin.write(input_str)
                bot["process"].stdin.flush()
                bot["state"] = "RUNNING"
                sent_count += 1
                broadcast_log(f"[{bot.get('model') or s}] [ACTION] Melanjutkan loop akun (Input: '{custom_num or 'ENTER'}')", device=s)
            except Exception:
                pass
                
    if sent_count > 0:
        return jsonify({"status": "success", "message": f"Sinyal lanjut terkirim ke {sent_count} perangkat"})
    return jsonify({"status": "error", "message": "Tidak ada bot yang sedang menunggu konfirmasi lanjut"}), 400

@app.route('/api/bot/pause', methods=['POST'])
def api_bot_pause():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    targets = [target] if target and target != "all" else list(device_bots.keys())
    sent_count = 0
    
    for s in targets:
        bot = device_bots.get(s)
        if bot and bot.get("process") and bot["process"].poll() is None:
            try:
                bot["process"].stdin.write("p\n")
                bot["process"].stdin.flush()
                bot["state"] = "WAITING_NEXT"
                sent_count += 1
                broadcast_log(f"[{bot.get('model') or s}] [ACTION] Sinyal PAUSE dikirim via Web UI", device=s)
            except Exception:
                pass
                
    if sent_count > 0:
        return jsonify({"status": "success", "message": f"Sinyal PAUSE terkirim ke {sent_count} perangkat"})
    return jsonify({"status": "error", "message": "Tidak ada bot yang sedang berjalan untuk di-pause"}), 400

@app.route('/api/bot/stop', methods=['POST'])
def api_bot_stop():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    targets = [target] if target and target != "all" else list(device_bots.keys())
    
    for s in targets:
        stop_single_device_bot(s)
        
    return jsonify({"status": "success", "message": "Bot pada perangkat target berhasil dihentikan"})

# ==============================================================================
# SPESIFIKASI ENDPOINT ACCOUNT CREATOR (MULTI-DEVICE)
# ==============================================================================

@app.route('/api/create_account/start', methods=['POST'])
def api_create_account_start():
    data = request.get_json(silent=True) or {}
    data["mode"] = "create_account"
    return api_bot_start()

@app.route('/api/create_account/stop', methods=['POST'])
def api_create_account_stop():
    return api_bot_stop()

@app.route('/api/create_account/next', methods=['POST'])
def api_create_account_next():
    return api_bot_next()

@app.route('/api/create_account/status', methods=['GET'])
def api_create_account_status():
    config = load_config_data()
    target = request.args.get("device")
    active_bot = device_bots.get(target, {}) if target else (list(device_bots.values())[0] if device_bots else {})
    
    return jsonify({
        "status": "success",
        "bot_state": active_bot.get("state", "IDLE"),
        "current_account": active_bot.get("current_clone", config.get("start_index", 1)),
        "next_account": active_bot.get("next_clone"),
        "current_referral_code": config.get("current_referral_code", "srTwuLUy"),
        "master_referral_code": config.get("master_referral_code", "srTwuLUy"),
        "total_emails_available": count_available_emails(),
        "is_running": (active_bot.get("process") is not None and active_bot["process"].poll() is None)
    })

@app.route('/api/create_account/referral/update', methods=['POST'])
def api_create_account_referral_update():
    data = request.get_json(silent=True) or {}
    code = (data.get("referral_code") or data.get("master_referral") or "").strip()
    if not code:
        return jsonify({"status": "error", "message": "Kode referral tidak boleh kosong"}), 400
    config = load_config_data()
    config["current_referral_code"] = code
    config["referral_code"] = code
    if data.get("master_referral"):
        config["master_referral_code"] = code
    save_config_data(config)
    broadcast_log(f"[CONFIG] Kode referral relay berhasil diupdate ke: {code}")
    return jsonify({
        "status": "success",
        "message": f"Kode referral berhasil diupdate ke: {code}",
        "current_referral_code": code,
        "master_referral_code": config.get("master_referral_code")
    })

@app.route('/api/wd/address/update', methods=['POST'])
def api_wd_address_update():
    data = request.get_json(silent=True) or {}
    addr = (data.get("alamat_wd") or data.get("address") or "").strip()
    if not addr:
        return jsonify({"status": "error", "message": "Alamat Stellar tujuan tidak boleh kosong"}), 400
    config = load_config_data()
    config["alamat_wd"] = addr
    save_config_data(config)
    broadcast_log(f"[CONFIG] Alamat Stellar WD berhasil diupdate ke: {addr}")
    return jsonify({
        "status": "success",
        "message": f"Alamat Stellar WD berhasil disimpan: {addr}",
        "alamat_wd": addr
    })

@app.route('/api/create_account/steps', methods=['GET'])
def api_create_account_steps():
    config = load_config_data()
    disabled_list = config.get("disabled_steps_create_account", [])
    steps = parse_steps_from_file(KORDINAT_CREATE_ACCOUNT_FILE, disabled_list)
    return jsonify({
        "status": "success",
        "mode": "create_account",
        "filepath": os.path.basename(KORDINAT_CREATE_ACCOUNT_FILE),
        "steps": steps,
        "count": len(steps)
    })

@app.route('/api/create_account/steps/toggle', methods=['POST'])
def api_create_account_step_toggle():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    enabled = data.get("enabled", True)
    if step_id is None:
        return jsonify({"status": "error", "message": "step_id diperlukan"}), 400
    update_kordinat_txt_step_file(KORDINAT_CREATE_ACCOUNT_FILE, step_id, not enabled)
    sync_kordinat_and_config()
    return jsonify({
        "status": "success",
        "message": f"Step {step_id} Buat Akun diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "step_id": step_id,
        "enabled": enabled
    })

@app.route('/api/create_account/steps/delay', methods=['POST'])
def api_create_account_step_delay():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    delay = data.get("delay")
    if step_id is None or delay is None:
        return jsonify({"status": "error", "message": "step_id dan delay diperlukan"}), 400
    try:
        f_delay = float(delay)
        update_sleep_in_kordinat(step_id, f_delay, filepath=KORDINAT_CREATE_ACCOUNT_FILE)
        return jsonify({"status": "success", "message": f"Delay step {step_id} Buat Akun diubah menjadi {f_delay}s"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal update delay: {e}"}), 500

@app.route('/api/create_account/steps/toggle_all', methods=['POST'])
def api_create_account_step_toggle_all():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)
    update_all_kordinat_txt_steps_file(KORDINAT_CREATE_ACCOUNT_FILE, not enabled)
    sync_kordinat_and_config()
    return jsonify({
        "status": "success",
        "message": f"Seluruh langkah Buat Akun diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "enabled": enabled
    })

# ==============================================================================
# ENDPOINT UMUM STEPS MACRO
# ==============================================================================

@app.route('/api/steps', methods=['GET'])
def api_steps():
    sync_kordinat_and_config()
    config = load_config_data()
    mode = request.args.get('mode') or request.args.get('type') or 'create_account'
    filepath = get_kordinat_file_by_mode(mode)
    
    if filepath == KORDINAT_CREATE_ACCOUNT_FILE:
        disabled_list = config.get("disabled_steps_create_account", [])
    elif filepath == KORDINAT_QRIS_MORPH_FILE:
        disabled_list = config.get("disabled_steps_qris_morph", [])
    elif filepath == KORDINAT_WD_BARU_FILE:
        disabled_list = config.get("disabled_steps_wd_baru", config.get("disabled_steps", []))
    elif filepath == KORDINAT_WD_OLD_FILE:
        disabled_list = config.get("disabled_steps_wd_old", config.get("disabled_steps", []))
    else:
        disabled_list = config.get("disabled_steps", [])
        
    steps = parse_steps_from_file(filepath, disabled_list)
    return jsonify({
        "status": "success",
        "mode": mode,
        "filepath": os.path.basename(filepath),
        "steps": steps,
        "count": len(steps)
    })

@app.route('/api/step/toggle', methods=['POST'])
def api_step_toggle():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    enabled = data.get("enabled", True)
    mode = data.get("mode") or data.get("type") or 'create_account'
    filepath = get_kordinat_file_by_mode(mode)
    
    if step_id is None:
        return jsonify({"status": "error", "message": "step_id diperlukan"}), 400
        
    set_off = not enabled
    update_kordinat_txt_step_file(filepath, step_id, set_off)
    sync_kordinat_and_config()
    
    return jsonify({
        "status": "success",
        "message": f"Step {step_id} ({os.path.basename(filepath)}) diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "step_id": step_id,
        "enabled": enabled,
        "mode": mode
    })

@app.route('/api/step/toggle_all', methods=['POST'])
def api_step_toggle_all():
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled", True)
    mode = data.get("mode") or data.get("type") or 'create_account'
    filepath = get_kordinat_file_by_mode(mode)
    
    set_off = not enabled
    update_all_kordinat_txt_steps_file(filepath, set_off)
    sync_kordinat_and_config()
    
    return jsonify({
        "status": "success",
        "message": f"Seluruh langkah ({os.path.basename(filepath)}) diubah menjadi {'AKTIF' if enabled else 'NONAKTIF'}",
        "enabled": enabled,
        "mode": mode
    })

@app.route('/api/step/delay', methods=['POST'])
def api_step_delay():
    data = request.get_json(silent=True) or {}
    step_id = data.get("step_id")
    delay = data.get("delay")
    mode = data.get("mode") or data.get("type") or 'create_account'
    filepath = get_kordinat_file_by_mode(mode)
    
    if step_id is None or delay is None:
        return jsonify({"status": "error", "message": "step_id dan delay diperlukan"}), 400
        
    try:
        f_delay = float(delay)
        update_sleep_in_kordinat(step_id, f_delay, filepath=filepath)
        return jsonify({
            "status": "success", 
            "message": f"Delay step {step_id} ({os.path.basename(filepath)}) diubah menjadi {f_delay}s",
            "step_id": step_id,
            "delay": f_delay
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal update delay: {e}"}), 500

# ==============================================================================
# CONFIG & HARDWARE UTILITIES (MULTI-DEVICE)
# ==============================================================================

@app.route('/api/config', methods=['POST'])
def api_config_update():
    data = request.get_json(silent=True) or {}
    config = load_config_data()
    
    if "alamat_wd" in data:
        config["alamat_wd"] = str(data["alamat_wd"]).strip()
    if "pin" in data:
        config["pin"] = str(data["pin"]).strip()
    if "start_index" in data:
        try:
            config["start_index"] = int(data["start_index"])
        except ValueError:
            pass
    if "last_wifi_ip" in data:
        config["last_wifi_ip"] = str(data["last_wifi_ip"]).strip()
    if "master_referral_code" in data:
        config["master_referral_code"] = str(data["master_referral_code"]).strip()
    if "current_referral_code" in data:
        config["current_referral_code"] = str(data["current_referral_code"]).strip()
        config["referral_code"] = config["current_referral_code"]
    if "target_device" in data:
        config["target_device"] = str(data["target_device"]).strip()
    if "step2_mode" in data:
        config["step2_mode"] = str(data["step2_mode"]).strip().lower()
        
    save_config_data(config)
    return jsonify({"status": "success", "message": "Konfigurasi berhasil disimpan", "config": config})

@app.route('/api/screen/set', methods=['POST'])
def api_screen_set():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    targets = [target] if target and target != "all" else [d["serial"] for d in get_unique_physical_devices()]
    
    results = []
    for s in targets:
        success, msg = record_and_apply_bot_screen(serial=s, silent=True)
        results.append({"serial": s, "success": success, "message": msg})
        
    return jsonify({
        "status": "success",
        "message": f"Format layar bot diterapkan pada {len(results)} perangkat",
        "results": results
    })

@app.route('/api/screen/restore', methods=['POST'])
def api_screen_restore():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    targets = [target] if target and target != "all" else [d["serial"] for d in get_unique_physical_devices()]
    
    for s in targets:
        restore_recorded_screen(serial=s, silent=True)
        
    return jsonify({"status": "success", "message": "Layar HP dikembalikan ke resolusi asli"})

@app.route('/api/scrcpy', methods=['POST'])
def api_scrcpy_launch():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    fps = int(data.get("fps", 120))
    
    try:
        if target and target != "all":
            dev_model = next((d["model"] for d in get_detailed_connected_devices() if d["serial"] == target), target)
            ok, msg = launch_scrcpy_mirror(target, dev_model, fps=fps)
            if ok:
                return jsonify({"status": "success", "message": msg})
            else:
                return jsonify({"status": "error", "message": msg}), 500
        else:
            # Buka scrcpy untuk semua perangkat fisik unik
            devices = get_unique_physical_devices()
            if not devices:
                return jsonify({"status": "error", "message": "Tidak ada perangkat Android terdeteksi"}), 400

            launched_count = 0
            for dev in devices:
                dev_model = dev.get("model") or dev["serial"]
                ok, _ = launch_scrcpy_mirror(dev["serial"], dev_model, fps=fps)
                if ok:
                    launched_count += 1
                time.sleep(0.3)
            return jsonify({
                "status": "success",
                "message": f"SCRCPY ({fps} FPS) untuk {launched_count} perangkat diluncurkan!"
            })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gagal membuka SCRCPY: {e}"}), 500

@app.route('/api/wallets', methods=['GET'])
def api_wallets():
    """Mengembalikan daftar seluruh file .txt di folder DATA WALLET BITGET."""
    wallets = get_available_wallet_files()
    config = load_config_data()
    return jsonify({
        "status": "success",
        "wallets": wallets,
        "active_wallet": config.get("active_wallet_file", wallets[0] if wallets else ""),
        "device_wallets": device_wallet_files
    })

@app.route('/api/device/wallet_file', methods=['POST'])
def api_device_wallet_file():
    """Menyetel file wallet TXT aktif untuk perangkat tertentu (mandiri per-PAD)."""
    data = request.get_json(silent=True) or {}
    serial = data.get("device")
    wallet_file = data.get("wallet_file")
    if not serial or not wallet_file:
        return jsonify({"status": "error", "message": "Perangkat dan nama file wallet diperlukan"}), 400
    
    device_wallet_files[serial] = wallet_file
    broadcast_log(f"[{serial}] [WALLET] File wallet aktif diatur ke: {wallet_file}", device=serial)
    return jsonify({
        "status": "success",
        "message": f"File wallet untuk {serial} berhasil disetel ke {wallet_file}",
        "device": serial,
        "wallet_file": wallet_file
    })

@app.route('/api/terminal/restart', methods=['POST'])
def api_terminal_restart():
    """Merestart server ADB dan me-reset stream log terminal secara aman tanpa error timeout."""
    adb_bin = get_adb_path()
    try:
        broadcast_log("[TERMINAL] Membersihkan proses ADB & Mirroring yang terkunci...")
        # 1. Hentikan proses scrcpy dan adb yang berpotensi menyandera port/device
        for proc in ["scrcpy.exe", "scrcpy-noconsole.exe", "QtScrcpy.exe", "QtScrcpy-noconsole.exe", "adb.exe"]:
            try:
                subprocess.run(["taskkill", "/F", "/T", "/IM", proc],
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                               capture_output=True, timeout=2)
            except Exception:
                pass

        # 2. Bebaskan port 5037 jika masih tersandera oleh PID asing
        try:
            net_proc = subprocess.run(["netstat", "-ano", "-p", "tcp"],
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                      capture_output=True, text=True, timeout=2)
            for line in (net_proc.stdout or "").splitlines():
                if ":5037 " in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        if pid not in ("0", "4", str(os.getpid())):
                            subprocess.run(["taskkill", "/F", "/PID", pid, "/T"],
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                           capture_output=True, timeout=2)
        except Exception:
            pass

        # 3. Beri jeda sistem Windows untuk melepaskan TCP socket
        time.sleep(0.8)

        # 4. Start ADB Server resmi project terlebih dahulu
        try:
            subprocess.run([adb_bin, "start-server"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                           capture_output=True, timeout=10)
        except Exception as e_start:
            broadcast_log(f"[TERMINAL WARNING] start-server warning: {e_start}")

        # 5. Bersihkan forwarding/reverse secara aman setelah server hidup (tidak boleh memblokir jika kosong)
        try:
            subprocess.run([adb_bin, "forward", "--remove-all"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                           capture_output=True, timeout=3)
            subprocess.run([adb_bin, "reverse", "--remove-all"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                           capture_output=True, timeout=3)
        except Exception:
            pass

        # 6. Baca daftar perangkat yang terpasang
        out = ""
        try:
            out_proc = subprocess.run([adb_bin, "devices", "-l"], capture_output=True, text=True,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=6)
            out = out_proc.stdout or ""
        except Exception as e_dev:
            out = f"Sedang sinkronisasi perangkat ({e_dev})"

        with log_lock:
            log_history.clear()
        broadcast_log("[TERMINAL] ADB Server berhasil di-restart dan log dibersihkan.")
        if out.strip():
            broadcast_log(f"[TERMINAL] Status perangkat ADB:\n{out.strip()}")
        return jsonify({
            "status": "success",
            "message": "ADB Server berhasil di-restart!",
            "output": out.strip()
        })
    except Exception as e:
        broadcast_log(f"[TERMINAL ERROR] Gagal restart ADB Server: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/screen/mode_screen_off', methods=['POST'])
def api_mode_screen_off():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    enabled = data.get("enabled", True)
    
    unique_devs = get_unique_physical_devices()
    targets = [target] if target and target != "all" else [d["serial"] for d in unique_devs]
    
    results = []
    for s in targets:
        ok, msg = set_screen_off_mode(s, enabled)
        results.append({"serial": s, "success": ok, "message": msg})
        
    return jsonify({
        "status": "success",
        "enabled": enabled,
        "results": results
    })

@app.route('/api/device/adb_command', methods=['POST'])
def api_device_adb_command():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    raw_cmd = (data.get("command") or "").strip()
    if not target or not raw_cmd:
        return jsonify({"status": "error", "message": "Perangkat dan perintah ADB diperlukan"}), 400

    adb_path = get_adb_path()

    if raw_cmd.lower().startswith("adb "):
        raw_cmd = raw_cmd[4:].strip()
    if raw_cmd.lower().startswith("-s "):
        parts = raw_cmd.split(maxsplit=2)
        if len(parts) >= 3:
            raw_cmd = parts[2]

    targets = [d["serial"] for d in get_unique_physical_devices()] if target == "all" else [target]
    outputs = {}
    threads = []
    out_lock = threading.Lock()

    def run_single_adb(s):
        first_token = raw_cmd.split()[0].lower() if raw_cmd.split() else ""
        if first_token == "keyevent":
            adb_args = [adb_path, "-s", s, "shell", "input", "keyevent"] + raw_cmd.split()[1:]
        elif first_token in ("input", "monkey", "am", "pm", "svc", "getprop", "setprop", "screencap", "dumpsys"):
            adb_args = [adb_path, "-s", s, "shell"] + raw_cmd.split()
        elif raw_cmd.lower().startswith("shell "):
            adb_args = [adb_path, "-s", s] + raw_cmd.split()
        else:
            adb_args = [adb_path, "-s", s, "shell"] + raw_cmd.split()

        broadcast_log(f"[{s}] [MANUAL ADB] {' '.join(adb_args[3:])}", device=s)
        try:
            res = subprocess.run(adb_args, capture_output=True, text=True, timeout=10,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out = (res.stdout or res.stderr or "").strip()
            if out:
                broadcast_log(f"[{s}] [OUTPUT] {out}", device=s)
            with out_lock:
                outputs[s] = out
        except Exception as e:
            broadcast_log(f"[{s}] [ERROR] {e}", device=s)
            with out_lock:
                outputs[s] = str(e)

    for s in targets:
        t = threading.Thread(target=run_single_adb, args=(s,), daemon=True)
        threads.append(t)
        t.start()
    for t in threads:
        t.join(timeout=10)

    return jsonify({"status": "success", "outputs": outputs, "output": list(outputs.values())[0] if outputs else ""})

@app.route('/api/step/step2_mode', methods=['GET', 'POST'])
def api_step2_mode():
    config = load_config_data()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        new_mode = (data.get("mode") or data.get("step2_mode") or "dompet").strip().lower()
        if new_mode in ("profil", "dompet"):
            config["step2_mode"] = new_mode
            save_config_data(config)
            set_off = (new_mode != "profil")
            update_kordinat_txt_step_file(KORDINAT_WD_BARU_FILE, 3, set_off)
            sync_kordinat_and_config()
            broadcast_log(f"[CONFIG] Mode Step 2 diatur ke: {new_mode.upper()} (Step 3 otomatis {'AKTIF' if new_mode == 'profil' else 'NONAKTIF'})")
            return jsonify({"status": "success", "step2_mode": new_mode, "step3_enabled": (new_mode == "profil")})
    return jsonify({"status": "success", "step2_mode": config.get("step2_mode", "dompet")})

def handle_qris_auto_tebar(targets, custom_tuyul=None, custom_amount=None):
    """Mengeksekusi Auto-Tebar token USDC On-Chain ke Tuyul berdasarkan deteksi layar/clipboard."""
    from qris_morph import BotRunner, get_last_tuyul_address, save_last_tuyul_address
    results = []
    for s in targets:
        try:
            runner = BotRunner(target_serial=s)
            chain_info = runner.wallet.get_chain_info()
            tok_symbol = chain_info.get("token_symbol", "USDC")
            net_name = chain_info.get("name", "Base Network")
            
            # 1. Alamat Tuyul (Prioritaskan clipboard/layar HP terkini dibanding cache lama)
            tuyul_addr = custom_tuyul or runner.adb.get_clipboard_text() or runner.adb.extract_evm_address_from_screen() or get_last_tuyul_address()
            if not (tuyul_addr and tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
                tuyul_addr = runner.adb.extract_evm_address_from_screen()
                
            if not (tuyul_addr and tuyul_addr.startswith("0x") and len(tuyul_addr) == 42):
                broadcast_log(f"[{s}] [AUTO-TEBAR ERROR] Address EVM Tuyul tidak terdeteksi dari layar/clipboard!", device=s)
                results.append({"serial": s, "success": False, "message": "Address Tuyul tidak terdeteksi"})
                continue
                
            save_last_tuyul_address(tuyul_addr)
            broadcast_log(f"[{s}] [AUTO-TEBAR] Target Tuyul: {tuyul_addr}", device=s)
            
            # 2. Nominal
            if custom_amount and float(custom_amount) > 0:
                send_amt = float(custom_amount)
            else:
                detected = runner.adb.read_required_usdc_from_screen()
                buffer_usdc = float(runner.config.get("usdc_buffer", 0.006))
                if detected:
                    send_amt = round(detected + buffer_usdc, 4)
                    broadcast_log(f"[{s}] [AUTO-TEBAR] Kebutuhan Layar: {detected} {tok_symbol} (+buffer {buffer_usdc})", device=s)
                else:
                    safe_rate = float(runner.config.get("fallback_rate", 17400.0))
                    cur_nom = int(runner.config.get("default_qris_nominal", 18501))
                    base_est = round(cur_nom / safe_rate, 4)
                    send_amt = round(base_est + buffer_usdc, 4)
                    broadcast_log(f"[{s}] [AUTO-TEBAR] Estimasi Kurs ({safe_rate}): {send_amt} {tok_symbol}", device=s)
                    
            # 3. Transfer On-Chain
            broadcast_log(f"[{s}] [AUTO-TEBAR] Mengirim {send_amt} {tok_symbol} ({net_name}) dari Wallet Tebar...", device=s)
            res = runner.wallet.send_token(tuyul_addr, send_amt)
            if res.get("success"):
                tx = res.get("tx_hash")
                broadcast_log(f"[{s}] [AUTO-TEBAR SUCCESS] Tx: {tx}", device=s)
                if res.get("explorer"):
                    broadcast_log(f"[{s}] [AUTO-TEBAR EXPLORER] {res.get('explorer')}", device=s)
                time.sleep(4.0)
                broadcast_log(f"[{s}] [AUTO-TEBAR] Saldo {send_amt} {tok_symbol} ({net_name}) terkirim ke Tuyul! Siap eksekusi Step 9.", device=s)
                results.append({"serial": s, "success": True, "tx": tx, "amount": send_amt, "token": tok_symbol})
            else:
                err = res.get("error", "Gagal transfer token")
                broadcast_log(f"[{s}] [AUTO-TEBAR ERROR] {err}", device=s)
                results.append({"serial": s, "success": False, "message": err})
        except Exception as e:
            broadcast_log(f"[{s}] [AUTO-TEBAR EXCEPTION] {e}", device=s)
            results.append({"serial": s, "success": False, "message": str(e)})
    return results

def handle_qris_reset_gaid(targets):
    """Mengeksekusi alur lengkap Reset GAID (Step 0.1 s/d 0.7) secara berurutan."""
    from qris_morph import BotRunner
    for s in targets:
        try:
            runner = BotRunner(target_serial=s)
            broadcast_log(f"[{s}] [SUB-TAP GAID] Menjalankan Alur Lengkap Reset GAID (0.1 s/d 0.7)...", device=s)
            for sid in ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7"]:
                broadcast_log(f"[{s}] [SUB-TAP GAID] Menjalankan Step {sid}...", device=s)
                runner.execute_macro_step(sid, force=True)
                time.sleep(0.5)
            broadcast_log(f"[{s}] [SUB-TAP GAID] Alur Step 0.1 s/d 0.7 (Reset GAID Lengkap) SELESAI!", device=s)
        except Exception as e:
            broadcast_log(f"[{s}] [SUB-TAP GAID ERROR] {e}", device=s)

@app.route('/api/qris/sub_command', methods=['POST'])
def api_qris_sub_command():
    """Endpoint untuk mengeksekusi sub-command dan sub-tap QRIS Morph."""
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    action = data.get("action") or data.get("sub_command")
    if not target or not action:
        return jsonify({"status": "error", "message": "Perangkat dan action diperlukan"}), 400
        
    targets = [d["serial"] for d in get_unique_physical_devices()] if target == "all" else [target]
    
    if action == "auto_tebar":
        custom_tuyul = data.get("tuyul_address")
        custom_amt = data.get("amount")
        def run_tebar():
            handle_qris_auto_tebar(targets, custom_tuyul, custom_amt)
        threading.Thread(target=run_tebar, daemon=True).start()
        return jsonify({"status": "success", "message": f"Auto-Tebar USDC dikirim ke {', '.join(targets)}", "action": action})
        
    elif action == "reset_gaid":
        def run_gaid():
            handle_qris_reset_gaid(targets)
        threading.Thread(target=run_gaid, daemon=True).start()
        return jsonify({"status": "success", "message": f"Reset GAID (0.1 - 0.7) dikirim ke {', '.join(targets)}", "action": action})
        
    elif action == "tap_amount":
        adb_path = get_adb_path()
        for s in targets:
            subprocess.run([adb_path, "-s", s, "shell", "input", "tap", "916", "1594"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            time.sleep(0.5)
            broadcast_log(f"[{s}] [SUB-TAP] Tap Kolom Jumlah (916, 1594)", device=s)
        return jsonify({"status": "success", "message": "Kolom Jumlah Pembayaran diketuk", "action": action})
        
    elif action == "tap_token":
        adb_path = get_adb_path()
        for s in targets:
            subprocess.run([adb_path, "-s", s, "shell", "input", "tap", "517", "1536"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            time.sleep(0.5)
            broadcast_log(f"[{s}] [SUB-TAP] Tap Token USDC (517, 1536)", device=s)
        return jsonify({"status": "success", "message": "Token USDC diketuk", "action": action})
        
    elif action == "tap_confirm":
        adb_path = get_adb_path()
        for s in targets:
            subprocess.run([adb_path, "-s", s, "shell", "input", "tap", "540", "2193"],
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            time.sleep(0.5)
            broadcast_log(f"[{s}] [SUB-TAP] Tap Konfirmasi Pembayaran (540, 2193)", device=s)
        return jsonify({"status": "success", "message": "Tombol Konfirmasi Pembayaran diketuk", "action": action})
        
    elif action == "type_pin":
        config = load_config_data()
        pin = config.get("pin", "080808")
        coords = config.get("keypad_coords_morph") or config.get("keypad_coords", {})
        adb_path = get_adb_path()
        for s in targets:
            for digit in str(pin):
                if digit in coords:
                    c = coords[digit]
                    if isinstance(c, dict):
                        kx = c.get('x')
                        ky = c.get('y')
                    elif isinstance(c, (list, tuple)) and len(c) >= 2:
                        kx, ky = c[0], c[1]
                    else:
                        kx, ky = None, None
                    if kx is not None and ky is not None:
                        subprocess.run([adb_path, "-s", s, "shell", "input", "tap", str(kx), str(ky)],
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        time.sleep(0.25)
            broadcast_log(f"[{s}] [SUB-TAP PIN] PIN {pin} diketik via keypad", device=s)
        return jsonify({"status": "success", "message": f"PIN {pin} diketik", "action": action})
        
    elif action == "open_notepad":
        if os.name == 'nt' and os.path.exists(KORDINAT_QRIS_MORPH_FILE):
            os.system(f'start notepad "{KORDINAT_QRIS_MORPH_FILE}"')
        return jsonify({"status": "success", "message": "Membuka file kordinat_qris_morph.txt di Notepad", "action": action})
        
    return jsonify({"status": "error", "message": f"Action {action} tidak dikenali"}), 400

@app.route('/api/step/execute', methods=['POST'])
def api_step_execute():
    data = request.get_json(silent=True) or {}
    target = data.get("device")
    step_id = data.get("step_id")
    sub_action = data.get("action") or data.get("sub_action")
    mode = data.get("mode") or "create_account"
    account_num = data.get("account_num", 1)

    if not target or step_id is None:
        return jsonify({"status": "error", "message": "Perangkat dan step_id diperlukan"}), 400

    targets = [d["serial"] for d in get_unique_physical_devices()] if target == "all" else [target]

    # Khusus QRIS Morph: Auto-Tebar, Reset GAID, Sub-Tap Step 9, dan Sub-Tap PIN
    str_step = str(step_id).lower()
    if str_step in ('auto_tebar', 'd') or sub_action == 'auto_tebar':
        custom_tuyul = data.get("tuyul_address")
        custom_amt = data.get("amount")
        def run_tebar():
            handle_qris_auto_tebar(targets, custom_tuyul, custom_amt)
        threading.Thread(target=run_tebar, daemon=True).start()
        return jsonify({
            "status": "success",
            "message": f"Auto-Tebar USDC dimulai pada {', '.join(targets)}",
            "devices": targets
        })

    if str_step in ('reset_gaid', 'i') or sub_action == 'reset_gaid':
        def run_gaid():
            handle_qris_reset_gaid(targets)
        threading.Thread(target=run_gaid, daemon=True).start()
        return jsonify({
            "status": "success",
            "message": f"Alur Lengkap Reset GAID (0.1 - 0.7) dimulai pada {', '.join(targets)}",
            "devices": targets
        })

    if (str_step == '9' and sub_action in ('tap_amount', 'tap_token', 'tap_confirm')) or sub_action in ('tap_amount', 'tap_token', 'tap_confirm'):
        adb_path = get_adb_path()
        coord_map = {
            'tap_amount': ("916 1594", "Kolom Jumlah Pembayaran (916, 1594)"),
            'tap_token': ("517 1536", "Token USDC Morph (517, 1536)"),
            'tap_confirm': ("540 2193", "Tombol Konfirmasi Pembayaran (540, 2193)")
        }
        coord, label = coord_map[sub_action]
        for s in targets:
            subprocess.run([adb_path, "-s", s, "shell", "input", "tap"] + coord.split(),
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            time.sleep(0.5)
            broadcast_log(f"[{s}] [SUB-TAP 9] Tap {label}", device=s)
        return jsonify({
            "status": "success",
            "message": f"Sub-tap {label} berhasil dieksekusi",
            "sub_action": sub_action,
            "devices": targets
        })

    if str_step in ('type_pin', 'p') or sub_action == 'type_pin':
        config = load_config_data()
        pin = config.get("pin", "080808")
        coords = config.get("keypad_coords_morph") or config.get("keypad_coords", {})
        adb_path = get_adb_path()
        for s in targets:
            for digit in str(pin):
                if digit in coords:
                    c = coords[digit]
                    if isinstance(c, dict):
                        kx = c.get('x')
                        ky = c.get('y')
                    elif isinstance(c, (list, tuple)) and len(c) >= 2:
                        kx, ky = c[0], c[1]
                    else:
                        kx, ky = None, None
                    if kx is not None and ky is not None:
                        subprocess.run([adb_path, "-s", s, "shell", "input", "tap", str(kx), str(ky)],
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                        time.sleep(0.25)
            broadcast_log(f"[{s}] [SUB-TAP PIN] PIN {pin} diketik via keypad", device=s)
        return jsonify({
            "status": "success",
            "message": f"Sub-tap PIN {pin} diketik",
            "devices": targets
        })

    # Khusus Step 2 dengan sub-action 'profil' atau 'dompet'
    if str(step_id) == '2' and sub_action in ('profil', 'dompet'):
        config = load_config_data()
        config["step2_mode"] = sub_action
        save_config_data(config)
        set_off = (sub_action != "profil")
        update_kordinat_txt_step_file(KORDINAT_WD_BARU_FILE, 3, set_off)
        sync_kordinat_and_config()

        adb_path = get_adb_path()
        coord = "78 119" if sub_action == "profil" else "197 284"
        label = "Profil Avatar (78, 119)" if sub_action == "profil" else "Dompet Saya (197, 284)"
        for s in targets:
            subprocess.run([adb_path, "-s", s, "shell", "input", "tap"] + coord.split(),
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            broadcast_log(f"[{s}] [MANUAL STEP 2] Tap {label}", device=s)
        return jsonify({
            "status": "success",
            "message": f"Step 2 ({label}) berhasil dieksekusi",
            "sub_action": sub_action,
            "step_id": step_id,
            "devices": targets,
            "step3_enabled": (sub_action == "profil")
        })

    filepath = get_kordinat_file_by_mode(mode)
    steps = parse_steps_from_file(filepath)
    target_step = next((s for s in steps if str(s["id"]) == str(step_id)), None)

    if not target_step:
        return jsonify({"status": "error", "message": f"Step {step_id} tidak ditemukan di {os.path.basename(filepath)}"}), 404

    custom_addr = data.get("alamat_wd")
    if custom_addr:
        cfg = load_config_data()
        cfg["alamat_wd"] = str(custom_addr).strip()
        save_config_data(cfg)

    def run_worker():
        threads = []
        for serial in targets:
            acc_num = account_num
            if serial in device_bots and device_bots[serial].get("current_clone"):
                acc_num = device_bots[serial]["current_clone"]
            t = threading.Thread(target=execute_step_commands, args=(serial, target_step, mode, acc_num), daemon=True)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    threading.Thread(target=run_worker, daemon=True).start()
    return jsonify({
        "status": "success",
        "message": f"Manual step {step_id} ({target_step['name']}) dikirim ke {', '.join(targets)}",
        "step_id": step_id,
        "step_name": target_step["name"],
        "devices": targets
    })

# ==============================================================================
# LOGGING REAL-TIME (SSE)
# ==============================================================================

@app.route('/api/logs', methods=['GET'])
def api_logs():
    filter_device = request.args.get("device")
    
    def event_stream():
        q = queue.Queue(maxsize=100)
        with subscribers_lock:
            subscribers.append(q)
            
        with log_lock:
            recent_logs = list(log_history)[-60:]

        try:
            for item in recent_logs:
                if not filter_device or filter_device == "all" or item.get("device") == filter_device or item.get("device") is None:
                    yield f"data: {json.dumps(item)}\n\n"

            while True:
                try:
                    item = q.get(timeout=15)
                    if not filter_device or filter_device == "all" or item.get("device") == filter_device or item.get("device") is None:
                        yield f"data: {json.dumps(item)}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        except Exception:
            pass
        finally:
            with subscribers_lock:
                if q in subscribers:
                    subscribers.remove(q)

    return Response(event_stream(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

@app.route('/api/logs/clear', methods=['POST'])
def api_logs_clear():
    with log_lock:
        log_history.clear()
    return jsonify({"status": "success", "message": "Log berhasil dibersihkan"})

def prevent_windows_sleep():
    """Mencegah Windows Sleep/Standby saat layar laptop mati agar bot & server tetap aktif 24/7."""
    if os.name == 'nt':
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_AWAYMODE_REQUIRED = 0x00000040
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
            return True
        except Exception:
            pass
    return False

# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == '__main__':
    prevent_windows_sleep()
    register_auto_restore()
    local_ip = get_local_machine_ip()
    unique_devs = get_unique_physical_devices()
    dev_info_str = ", ".join([f"{d['model']} ({d['serial']})" for d in unique_devs]) if unique_devs else "Tidak Ada Perangkat"
    
    # Format otomatis seluruh layar device yang terkoneksi ke bot screen saat server start
    for dev in unique_devs:
        record_and_apply_bot_screen(serial=dev["serial"], silent=True)

    # Start Cloudflare Tunnel otomatis di background
    start_cloudflare_tunnel(local_ip, PORT)
    atexit.register(stop_cloudflare_tunnel)
    
    print("=========================================================")
    print("   BITGET WALLET & BOT CONTROL SERVER (PORT 2000)        ")
    print("   TOPNOD MULTI-DEVICE & CLOUDFLARE TUNNEL ACTIVE        ")
    print("=========================================================")
    print(f" Akses LAN Otomatis : http://{local_ip}:{PORT}          ")
    print(f" Domain Cloudflare  : https://{PUBLIC_DOMAIN}           ")
    print(f" Terdeteksi Device  : {dev_info_str}")
    print(" Format Layar Bot   : Otomatis 1080x2400 @ 352 DPI Aktif ")
    print(" Mode Anti-Sleep    : AKTIF (Laptop bekerja 24/7 saat layar mati)")
    print(f" Status Binding     : LOCKED MURNI http://{HOST}:{PORT}")
    print("=========================================================")
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    print(f" * Running on http://{HOST}:{PORT} (Pure Local LAN IP)")
    print(" * Tekan CTRL+C untuk menghentikan server.")
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
