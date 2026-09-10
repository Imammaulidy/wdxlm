import os
import sys
import json
import re
import subprocess
import platform
import atexit
import signal

# Direktori & File Cache
CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))
SCREEN_CACHE_FILE = os.path.join(CORE_DIR, '.screen_cache.json')

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

def run_adb(cmd):
    """Menjalankan perintah ADB dan mengembalikan output stdout."""
    try:
        r = subprocess.run(
            f'adb {cmd}',
            shell=True,
            capture_output=True,
            text=True
        )
        return r.stdout.strip()
    except Exception:
        return ""

def get_connected_devices():
    """Mengecek apakah ada HP Android yang terhubung via ADB."""
    out = run_adb("devices")
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices

def read_current_screen():
    """
    Membaca resolusi dan DPI yang sedang aktif dan fisik dari HP via ADB.
    Return dictionary detail.
    """
    size_out = run_adb("shell wm size")
    density_out = run_adb("shell wm density")

    info = {
        "physical_size": None,
        "override_size": None,
        "active_size": None,
        "physical_density": None,
        "override_density": None,
        "active_density": None
    }

    m_phys_s = re.search(r"Physical size:\s*(\d+x\d+)", size_out, re.IGNORECASE)
    if m_phys_s:
        info["physical_size"] = m_phys_s.group(1).strip()

    m_over_s = re.search(r"Override size:\s*(\d+x\d+)", size_out, re.IGNORECASE)
    if m_over_s:
        info["override_size"] = m_over_s.group(1).strip()

    info["active_size"] = info["override_size"] or info["physical_size"]

    m_phys_d = re.search(r"Physical density:\s*(\d+)", density_out, re.IGNORECASE)
    if m_phys_d:
        info["physical_density"] = m_phys_d.group(1).strip()

    m_over_d = re.search(r"Override density:\s*(\d+)", density_out, re.IGNORECASE)
    if m_over_d:
        info["override_density"] = m_over_d.group(1).strip()

    info["active_density"] = info["override_density"] or info["physical_density"]

    return info

def get_cached_screen():
    """Membaca rekaman ukuran asli HP dari file cache (.screen_cache.json)."""
    if os.path.exists(SCREEN_CACHE_FILE):
        try:
            with open(SCREEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("original_size"), data.get("original_density")
        except Exception:
            pass
    return None, None

def save_cached_screen(size, density):
    """Menyimpan rekaman ukuran asli HP ke file cache."""
    try:
        with open(SCREEN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "original_size": str(size),
                "original_density": str(density)
            }, f, indent=4)
    except Exception as e:
        print(f"[!] Gagal menyimpan cache resolusi: {e}")

def clear_cached_screen():
    """Menghapus file cache setelah resolusi berhasil dikembalikan."""
    if os.path.exists(SCREEN_CACHE_FILE):
        try:
            os.remove(SCREEN_CACHE_FILE)
        except Exception:
            pass

_is_bot_screen_active = False

def record_and_apply_bot_screen(silent=False):
    """
    1. Otomatis merekam resolusi & DPI yang sedang digunakan oleh HP saat ini.
    2. Otomatis mengubah resolusi HP ke standar bot (1080x2400 @ 352 DPI).
    """
    global _is_bot_screen_active

    devices = get_connected_devices()
    if not devices:
        if not silent:
            print("[!] Peringatan: Tidak ada perangkat HP terdeteksi via ADB untuk rekaman layar.")
        return False, "Tidak ada perangkat terhubung"

    cached_size, cached_density = get_cached_screen()
    orig_size = cached_size
    orig_density = cached_density

    # Jika belum ada cache, rekam ukuran aktif dari HP saat ini
    if not orig_size or not orig_density:
        info = read_current_screen()
        if not info["active_size"] or not info["active_density"]:
            return False, "Gagal membaca resolusi layar dari HP"

        # Jika HP kebetulan sedang berada di 352 DPI (misal bot sebelumnya belum restore),
        # utamakan physical density agar ukuran asli yang terekam adalah ukuran bawaan HP
        if info["active_density"] == "352" and info["physical_density"] and info["physical_density"] != "352":
            orig_density = info["physical_density"]
        else:
            orig_density = info["active_density"]

        if info["active_size"] == "1080x2400" and info["physical_size"]:
            orig_size = info["physical_size"]
        else:
            orig_size = info["active_size"]

        save_cached_screen(orig_size, orig_density)
        if not silent:
            print(f"[*] [AUTO-RECORD] Resolusi & DPI asli HP terekam: {orig_size} @ {orig_density} DPI")
    else:
        if not silent:
            print(f"[*] [CACHE] Menggunakan resolusi asli HP terekam: {orig_size} @ {orig_density} DPI")

    # Terapkan resolusi bot
    if not silent:
        print("[*] Menyesuaikan layar otomatis ke format bot (1080x2400 @ 352 DPI)...")
    run_adb("shell wm size 1080x2400")
    run_adb("shell wm density 352")
    _is_bot_screen_active = True
    return True, f"{orig_size} @ {orig_density} DPI"

def restore_recorded_screen(silent=False):
    """
    Restore resolusi dan DPI ke ukuran asli HP yang SUDAH DIREKAM sebelumnya.
    BUKAN mereset ke ukuran pabrik (wm reset), melainkan tepat ke nilai yang terekam.
    """
    global _is_bot_screen_active

    orig_size, orig_density = get_cached_screen()

    # Cek apakah ada HP yang terhubung
    devices = get_connected_devices()
    if not devices:
        clear_cached_screen()
        _is_bot_screen_active = False
        return False

    if orig_size and orig_density:
        if not silent:
            print(f"\n[*] Mengembalikan layar HP ke ukuran asli yang sudah direkam ({orig_size} @ {orig_density} DPI)...")
        run_adb(f"shell wm size {orig_size}")
        run_adb(f"shell wm density {orig_density}")
        clear_cached_screen()
        _is_bot_screen_active = False
        if not silent:
            print(f"[V] Layar HP berhasil dikembalikan ke {orig_size} @ {orig_density} DPI!")
        return True
    else:
        # Fallback jika cache tidak ada: baca physical info lalu set ke physical (bukan reset)
        info = read_current_screen()
        if info.get("physical_size") and info.get("physical_density"):
            p_size = info["physical_size"]
            p_density = info["physical_density"]
            if not silent:
                print(f"\n[*] Mengembalikan layar HP ke ukuran fisik HP: {p_size} @ {p_density} DPI...")
            run_adb(f"shell wm size {p_size}")
            run_adb(f"shell wm density {p_density}")
            _is_bot_screen_active = False
            return True
    return False

# Persistent handler reference to avoid garbage collection on Windows ctypes
_ctrl_handler_ref = None
_handlers_registered = False

def register_auto_restore():
    """
    Mendaftarkan listener untuk memulihkan resolusi saat terminal ditutup / exit:
    - atexit (Normal exit, sys.exit)
    - SIGINT (Ctrl+C), SIGTERM
    - SetConsoleCtrlHandler di Windows (ketika tombol close [X] terminal diklik)
    """
    global _ctrl_handler_ref, _handlers_registered
    if _handlers_registered:
        return
    _handlers_registered = True

    atexit.register(restore_recorded_screen, silent=False)

    def _sig_handler(sig, frame):
        restore_recorded_screen(silent=False)
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _sig_handler)
    except Exception:
        pass
    try:
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    if platform.system() == "Windows":
        try:
            import ctypes
            def _win_ctrl_handler(ctrl_type):
                # 0=CTRL_C, 1=CTRL_BREAK, 2=CTRL_CLOSE, 5=LOGOFF, 6=SHUTDOWN
                restore_recorded_screen(silent=False)
                return False

            _ctrl_handler_ref = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(_win_ctrl_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_ctrl_handler_ref, True)
        except Exception:
            pass
