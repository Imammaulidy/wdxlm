import os
import sys
import json
import re
import socket
import subprocess
import time

from paths import CORE_DIR, PROJECT_ROOT, CONFIG_PATH as CONFIG_FILE, SCRCPY_DIR, SCRCPY_EXE


# Tambahkan scrcpy ke PATH agar perintah adb/scrcpy selalu tersedia
if SCRCPY_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = SCRCPY_DIR + os.pathsep + os.environ.get("PATH", "")

def run_cmd(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(data):
    try:
        current = load_config()
        current.update(data)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current, f, indent=4)
    except Exception:
        pass

def is_port_reachable(ip, port=5555, timeout=1.5):
    """Cek cepat apakah port terbuka via TCP socket (menghindari adb hang jika offline)."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def hide_console():
    """Menyembunyikan jendela terminal console setelah scrcpy berhasil tampil di layar."""
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # 0 = SW_HIDE
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

def ensure_adb_server():
    """Pastikan daemon ADB server sudah aktif tanpa memblokir I/O pipe."""
    if not is_port_reachable("127.0.0.1", 5037, timeout=0.5):
        os.system("adb start-server >nul 2>&1")

def get_connected_devices():
    """Mengembalikan tuple (list_usb_devices, list_tcp_devices)"""
    ensure_adb_server()
    out = run_cmd("adb devices")
    usb_devs = []
    tcp_devs = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            if ":" in serial:
                tcp_devs.append(serial)
            else:
                usb_devs.append(serial)
    return usb_devs, tcp_devs

def detect_wifi_ip(target_serial=None):
    """
    Mendeteksi IP Wi-Fi murni dari interface wlan0 atau wlan1.
    TIDAK AKAN membaca interface seluler/data (rmnet) atau loopback.
    """
    prefix = f"adb -s {target_serial} " if target_serial else "adb -d "
    for iface in ["wlan0", "wlan1"]:
        out = run_cmd(f"{prefix}shell ip -f inet addr show {iface}", timeout=3)
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m:
            ip = m.group(1)
            # Pastikan bukan loopback
            if not ip.startswith("127."):
                return ip
    return None

def launch_scrcpy(target_serial):
    """Meluncurkan SCRCPY secara headless tanpa jendela konsol hitam."""
    if not os.path.exists(SCRCPY_EXE):
        print(f"[!] File scrcpy.exe tidak ditemukan di: {SCRCPY_DIR}")
        return False

    cmd = [SCRCPY_EXE, "-s", target_serial, "-S", "-w", "--max-fps=120"]
    flags = 0x08000000 if sys.platform == "win32" else 0
    try:
        p = subprocess.Popen(cmd, cwd=SCRCPY_DIR, creationflags=flags)
        time.sleep(1.0)
        if p.poll() is not None and p.poll() != 0:
            # Fallback tanpa flag -S jika firmware device tidak mendukung
            p = subprocess.Popen([SCRCPY_EXE, "-s", target_serial, "-w", "--max-fps=120"], cwd=SCRCPY_DIR, creationflags=flags)
            time.sleep(1.0)

        if p.poll() is None:
            print("[+] SCRCPY aktif di layar monitor Anda (120 FPS).")
            hide_console()
            return True
        else:
            print(f"[!] Scrcpy gagal dimulai (kode keluar: {p.poll()}).")
            return False
    except Exception as e:
        print(f"[!] Gagal menjalankan scrcpy: {e}")
        return False

def mode_usb_pure():
    """Mode USB Murni (120 FPS, Zero Latency)"""
    print("=========================================================")
    print("      SCRCPY MODE USB MURNI (120 FPS - ZERO LATENCY)     ")
    print("=========================================================")
    usb_devs, tcp_devs = get_connected_devices()
    if not usb_devs:
        print("[!] Perangkat USB tidak terdeteksi!")
        print("    1. Pastikan kabel USB tercolok ke HP dan PC.")
        print("    2. Aktifkan Opsi Pengembang -> Debugging USB di HP.")
        return False

    usb_dev = usb_devs[0]
    print(f"[+] Terdeteksi perangkat USB : {usb_dev}")
    
    # Putuskan sambungan wireless jika ada agar tidak bentrok
    if tcp_devs:
        print("[*] Memutuskan koneksi wireless agar terkunci ke kabel USB...")
        run_cmd("adb disconnect", timeout=2)

    # Catat Wi-Fi IP untuk referensi di masa depan
    try:
        ip = detect_wifi_ip(usb_dev)
        if ip:
            save_config({"last_wifi_ip": ip})
    except Exception:
        pass

    print("[*] Meluncurkan SCRCPY via USB murni...")
    ok = launch_scrcpy(usb_dev)
    if ok:
        time.sleep(1.5)
        sys.exit(0)
    return ok

def mode_switch_wireless():
    """Beralih dari USB ke Wireless dan Meluncurkan SCRCPY (120 FPS)"""
    print("=========================================================")
    print("    SWITCH KE WIRELESS & JALANKAN SCRCPY (120 FPS)      ")
    print("=========================================================")
    usb_devs, tcp_devs = get_connected_devices()

    # Jika sudah ada koneksi wireless aktif
    for dev in tcp_devs:
        ip_part = dev.split(":")[0]
        port_part = int(dev.split(":")[1]) if ":" in dev else 5555
        if is_port_reachable(ip_part, port_part, timeout=1.0):
            print(f"[+] Menggunakan koneksi wireless yang sudah aktif: {dev}")
            print("[*] Meluncurkan SCRCPY...")
            ok = launch_scrcpy(dev)
            if ok:
                time.sleep(1.5)
                sys.exit(0)
            return ok

    # Butuh USB untuk inisialisasi awal
    if not usb_devs:
        config = load_config()
        last_ip = config.get("last_wifi_ip", "")
        if last_ip and is_port_reachable(last_ip, 5555, timeout=1.5):
            print(f"[*] Mencoba menyambung ke IP terakhir: {last_ip}:5555...")
            run_cmd(f"adb connect {last_ip}:5555", timeout=3)
            ok = launch_scrcpy(f"{last_ip}:5555")
            if ok:
                time.sleep(1.5)
                sys.exit(0)
            return ok
        print("[ERROR] Tidak ada perangkat USB yang terhubung untuk inisialisasi wireless!")
        print("        Colokkan kabel USB ke HP sebentar untuk mengaktifkan port 5555.")
        return False

    usb_dev = usb_devs[0]
    print(f"[*] Mengambil IP Wi-Fi dari perangkat USB ({usb_dev})...")
    ip = detect_wifi_ip(usb_dev)
    if not ip:
        print("[ERROR] Gagal mendeteksi IP Wi-Fi perangkat!")
        print("        Pastikan HP sudah terhubung ke jaringan Wi-Fi yang sama dengan PC.")
        return False

    print(f"[+] IP Wi-Fi Terdeteksi: {ip}")
    save_config({"last_wifi_ip": ip})

    print("[*] Mengaktifkan mode TCP/IP pada port 5555...")
    run_cmd(f"adb -s {usb_dev} tcpip 5555", timeout=5)
    time.sleep(1.5)

    print(f"[*] Menghubungkan ADB ke {ip}:5555...")
    res = run_cmd(f"adb connect {ip}:5555", timeout=5)
    print(f"    > {res}")
    time.sleep(1.0)

    target_dev = f"{ip}:5555"
    print("\n=========================================================")
    print(f" [SUKSES BESAR] Mode Wireless AKTIF di: {target_dev}")
    print(" [INFO PENTING] ANDA SEKARANG SUDAH AMAN UNTUK MENCABUT KABEL USB!")
    print("=========================================================\n")

    print("[*] Meluncurkan SCRCPY Wireless (120 FPS)...")
    ok = launch_scrcpy(target_dev)
    if ok:
        time.sleep(2.0)
        sys.exit(0)
    return ok

def mode_setup_wireless_only():
    """Hanya Mengaktifkan ADB Wireless tanpa Membuka Layar GUI"""
    print("=========================================================")
    print("       AKTIFKAN ADB WIRELESS (UNTUK PENGGUNAAN BOT)      ")
    print("=========================================================")
    usb_devs, tcp_devs = get_connected_devices()
    if tcp_devs:
        print(f"[+] ADB Wireless sudah aktif di: {tcp_devs[0]}")
        return True

    if not usb_devs:
        print("[ERROR] Colokkan kabel USB ke HP terlebih dahulu!")
        return False

    usb_dev = usb_devs[0]
    ip = detect_wifi_ip(usb_dev)
    if not ip:
        print("[ERROR] Gagal membaca IP Wi-Fi! Pastikan Wi-Fi HP aktif.")
        return False

    print(f"[+] IP Wi-Fi HP: {ip}")
    save_config({"last_wifi_ip": ip})

    print("[*] Mengaktifkan TCP/IP port 5555...")
    run_cmd(f"adb -s {usb_dev} tcpip 5555", timeout=5)
    time.sleep(1.5)

    print(f"[*] Menyambungkan ke {ip}:5555...")
    res = run_cmd(f"adb connect {ip}:5555", timeout=5)
    print(f"    > {res}")
    print("\n[SUKSES] ADB Wireless aktif! Kabel USB sekarang boleh dicabut.\n")
    return True

def mode_disconnect():
    print("[*] Memutuskan semua sambungan ADB TCP/IP...")
    run_cmd("adb disconnect", timeout=3)
    print("[OK] Semua koneksi wireless berhasil diputus.")

def mode_info():
    print("=========================================================")
    print("                INFORMASI DETAIL PERANGKAT ADB           ")
    print("=========================================================")
    usb_devs, tcp_devs = get_connected_devices()
    print(f" Perangkat USB      : {', '.join(usb_devs) if usb_devs else 'Tidak Terhubung'}")
    print(f" Perangkat Wireless : {', '.join(tcp_devs) if tcp_devs else 'Tidak Terhubung'}")
    dev = usb_devs[0] if usb_devs else (tcp_devs[0] if tcp_devs else None)
    if dev:
        model = run_cmd(f"adb -s {dev} shell getprop ro.product.model")
        print(f" Model HP           : {model}")
        bat = run_cmd(f"adb -s {dev} shell dumpsys battery")
        m = re.search(r"level:\s+(\d+)", bat)
        if m:
            print(f" Baterai HP         : {m.group(1)}%")
        ip = detect_wifi_ip(dev)
        if ip:
            print(f" IP Wi-Fi           : {ip}")
    print("=========================================================")

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--get-ip":
            target = sys.argv[2] if len(sys.argv) > 2 else None
            ip = detect_wifi_ip(target)
            if ip:
                print(ip)
            sys.exit(0)
        elif arg == "--usb":
            mode_usb_pure()
            sys.exit(0)
        elif arg == "--switch-wireless":
            mode_switch_wireless()
            sys.exit(0)
        elif arg == "--setup-wireless-only":
            mode_setup_wireless_only()
            sys.exit(0)
        elif arg == "--disconnect":
            mode_disconnect()
            sys.exit(0)
        elif arg == "--info":
            mode_info()
            sys.exit(0)

    # Default auto-detect
    usb_devices, tcp_devices = get_connected_devices()
    if usb_devices:
        mode_usb_pure()
    elif tcp_devices:
        mode_switch_wireless()
    else:
        config = load_config()
        last_ip = config.get("last_wifi_ip", "")
        if last_ip:
            mode_switch_wireless()
        else:
            mode_usb_pure()

if __name__ == "__main__":
    main()
