import os
import sys
import json
import re
import atexit
import signal
import platform
import subprocess

from paths import CORE_DIR, PROJECT_ROOT, SCRCPY_DIR, JSON_DIR
SCREEN_CACHE_FILE = os.path.join(JSON_DIR, '.screen_cache.json')

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Setup PATH untuk scrcpy & adb jika di Windows
if not IS_TERMUX:
    candidates = [
        SCRCPY_DIR,
        os.path.join(PROJECT_ROOT, "Core", "scrcpy-win64-v3.3.4"),
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

def run_adb(cmd, serial=None):
    """Menjalankan perintah ADB dan mengembalikan output stdout."""
    target = serial or os.environ.get("ANDROID_SERIAL")
    prefix = f'adb -s {target} ' if target else 'adb '
    try:
        r = subprocess.run(
            f'{prefix}{cmd}',
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
        if not line or line.startswith("List") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices

_DEVICE_MARKET_NAME_CACHE = {}

KNOWN_DEVICE_MODELS = {
    "22021211RG": "POCO F4",
    "21061110AG": "POCO X3 GT",
    "2201116PG": "POCO X4 Pro 5G",
    "23049PCD8G": "POCO F5",
    "2311DRK48G": "POCO X6 Pro",
    "24053PY09G": "POCO F6",
    "M2012K11AG": "POCO F3",
    "M2007J20CG": "POCO X3 NFC",
    "M2102J20SG": "POCO X3 Pro"
}

def get_device_market_name(serial, raw_model=None):
    """Membaca nama komersial HP (misal: POCO F4, POCO X3 GT) dengan caching cepat."""
    if not serial:
        return ""
    if serial in _DEVICE_MARKET_NAME_CACHE:
        return _DEVICE_MARKET_NAME_CACHE[serial]

    # Cek kamus model cepat
    if raw_model and raw_model in KNOWN_DEVICE_MODELS:
        name = KNOWN_DEVICE_MODELS[raw_model]
        _DEVICE_MARKET_NAME_CACHE[serial] = name
        return name

    # Ambil langsung dari getprop ro.product.marketname
    name = run_adb("shell getprop ro.product.marketname", serial=serial).strip()
    if not name or name.lower() == "unknown":
        model_str = raw_model or run_adb("shell getprop ro.product.model", serial=serial).strip()
        if model_str in KNOWN_DEVICE_MODELS:
            name = KNOWN_DEVICE_MODELS[model_str]
        else:
            brand = run_adb("shell getprop ro.product.brand", serial=serial).strip()
            if brand and model_str and not model_str.upper().startswith(brand.upper()):
                name = f"{brand.upper()} {model_str}"
            elif model_str:
                name = model_str
            else:
                name = "Android"

    _DEVICE_MARKET_NAME_CACHE[serial] = name
    return name

def get_detailed_connected_devices():
    """Mengembalikan daftar detail seluruh perangkat yang terhubung beserta nama komersialnya."""
    try:
        r = subprocess.run("adb devices -l", shell=True, capture_output=True, text=True, timeout=4)
        out = r.stdout
    except Exception:
        out = ""
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            raw_model = "Android"
            product = ""
            for p in parts[2:]:
                if p.startswith("model:"):
                    raw_model = p.split(":", 1)[1]
                elif p.startswith("product:"):
                    product = p.split(":", 1)[1]

            market_name = get_device_market_name(serial, raw_model)
            full_model_name = f"{market_name} [{raw_model}]" if (market_name and market_name.lower() != raw_model.lower()) else (market_name or raw_model)

            devices.append({
                "serial": serial,
                "model": market_name or raw_model,
                "raw_model": raw_model,
                "full_model": full_model_name,
                "product": product,
                "is_wifi": (":" in serial),
                "display_name": f"{market_name or raw_model} ({serial})"
            })
    return devices

def read_current_screen(serial=None):
    """
    Membaca resolusi dan DPI yang sedang aktif dan fisik dari HP via ADB.
    Return dictionary detail.
    """
    size_out = run_adb("shell wm size", serial=serial)
    density_out = run_adb("shell wm density", serial=serial)

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

    info["font_scale"] = run_adb("shell settings get system font_scale", serial=serial).strip() or "1.0"
    return info

def get_cached_screen(serial=None):
    """Membaca rekaman ukuran asli HP dari file cache (.screen_cache.json)."""
    if os.path.exists(SCREEN_CACHE_FILE):
        try:
            with open(SCREEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if serial and serial in data and isinstance(data[serial], dict):
                    return data[serial].get("original_size"), data[serial].get("original_density"), data[serial].get("original_font_scale")
                return data.get("original_size"), data.get("original_density"), data.get("original_font_scale")
        except Exception:
            pass
    return None, None, None

def save_cached_screen(size, density, font_scale=None, serial=None):
    """Menyimpan rekaman ukuran asli HP ke file cache."""
    try:
        data = {}
        if os.path.exists(SCREEN_CACHE_FILE):
            try:
                with open(SCREEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        item = {
            "original_size": str(size),
            "original_density": str(density)
        }
        if font_scale:
            item["original_font_scale"] = str(font_scale)
        if serial:
            data[serial] = item
        data["original_size"] = str(size)
        data["original_density"] = str(density)
        if font_scale:
            data["original_font_scale"] = str(font_scale)
        with open(SCREEN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[!] Gagal menyimpan cache resolusi: {e}")

def clear_cached_screen(serial=None):
    """Menghapus file cache setelah resolusi berhasil dikembalikan."""
    if os.path.exists(SCREEN_CACHE_FILE):
        try:
            if serial:
                with open(SCREEN_CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if serial in data:
                    del data[serial]
                if data:
                    with open(SCREEN_CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    return
            os.remove(SCREEN_CACHE_FILE)
        except Exception:
            pass

_is_bot_screen_active = False
_already_restored = False

def record_and_apply_bot_screen(serial=None, silent=False):
    """
    1. Otomatis membaca & merekam resolusi, DPI & font_scale aktif dari HP.
    2. Menyesuaikan resolusi HP ke standar bot (1080x2400 @ 352 DPI) dan font_scale 0.81 agar seragam.
    """
    global _is_bot_screen_active, _already_restored

    devices = get_connected_devices()
    if not devices:
        if not silent:
            print("[!] Peringatan: Tidak ada perangkat HP terdeteksi via ADB untuk rekaman layar.")
        return False, "Tidak ada perangkat terhubung"

    target_dev = serial or (devices[0] if len(devices) == 1 else None)
    cached_size, cached_density, cached_font = get_cached_screen(target_dev)
    orig_size = cached_size
    orig_density = cached_density
    orig_font = cached_font

    # Jika belum ada cache, rekam ukuran aktif dari HP saat ini APA ADANYA
    if not orig_size or not orig_density:
        info = read_current_screen(target_dev)
        if not info["active_size"] or not info["active_density"]:
            return False, "Gagal membaca resolusi layar dari HP"

        orig_size = info["active_size"]
        orig_density = info["active_density"]
        orig_font = info.get("font_scale") or "1.0"

        save_cached_screen(orig_size, orig_density, orig_font, target_dev)
        if not silent:
            tag = f"[{target_dev}] " if target_dev else ""
            print(f"[*] {tag}[AUTO-RECORD] Resolusi & DPI asli HP terekam: {orig_size} @ {orig_density} DPI (Font: {orig_font})")
    else:
        if not silent:
            tag = f"[{target_dev}] " if target_dev else ""
            print(f"[*] {tag}[CACHE] Menggunakan resolusi asli HP terekam: {orig_size} @ {orig_density} DPI")

    # Terapkan resolusi bot jika berbeda dari 1080x2400 @ 352 DPI
    curr_info = read_current_screen(target_dev)
    if curr_info.get("active_size") != "1080x2400" or curr_info.get("active_density") != "352":
        if not silent:
            tag = f"[{target_dev}] " if target_dev else ""
            print(f"[*] {tag}Menyesuaikan layar otomatis ke format bot (1080x2400 @ 352 DPI)...")
        run_adb("shell wm size 1080x2400", serial=target_dev)
        run_adb("shell wm density 352", serial=target_dev)
    else:
        if not silent:
            tag = f"[{target_dev}] " if target_dev else ""
            print(f"[*] {tag}Layar HP sudah berada pada standar bot (1080x2400 @ 352 DPI).")

    # Samakan font scale ke 0.81 (standar bot)
    run_adb("shell settings put system font_scale 0.81", serial=target_dev)

    _is_bot_screen_active = True
    _already_restored = False
    return True, f"{orig_size} @ {orig_density} DPI"

def restore_recorded_screen(serial=None, silent=False):
    """
    Restore resolusi, DPI dan font_scale tepat ke ukuran asli HP yang SUDAH DIREKAM sebelumnya.
    """
    global _is_bot_screen_active, _already_restored

    devices = get_connected_devices()
    if not devices:
        clear_cached_screen()
        _is_bot_screen_active = False
        _already_restored = True
        return False

    targets = [serial] if serial else devices
    restored_any = False

    for dev in targets:
        orig_size, orig_density, orig_font = get_cached_screen(dev)
        if orig_size and orig_density:
            if not silent:
                print(f"\n[*] [{dev}] Mengembalikan layar HP ke ukuran asli ({orig_size} @ {orig_density} DPI)...")
            run_adb(f"shell wm size {orig_size}", serial=dev)
            run_adb(f"shell wm density {orig_density}", serial=dev)
            if orig_font:
                run_adb(f"shell settings put system font_scale {orig_font}", serial=dev)
            restored_any = True

    clear_cached_screen(serial)
    _is_bot_screen_active = False
    _already_restored = True
    return restored_any

_ctrl_handler_ref = None
_handlers_registered = False

def register_auto_restore():
    """
    Mendaftarkan listener untuk memulihkan resolusi saat terminal ditutup / exit.
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
                if ctrl_type in (2, 5, 6):
                    restore_recorded_screen(silent=True)
                    return True
                return False

            _ctrl_handler_ref = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)(_win_ctrl_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(_ctrl_handler_ref, True)
        except Exception:
            pass
