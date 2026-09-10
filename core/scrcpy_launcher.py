import os
import sys
import json
import re
import socket
import subprocess
import time

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, ".."))
CONFIG_FILE = os.path.join(CORE_DIR, "config.json")
SCRCPY_DIR = os.path.join(CORE_DIR, "scrcpy-win64-v3.3.4")
SCRCPY_EXE = os.path.join(SCRCPY_DIR, "scrcpy.exe")

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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def is_port_reachable(ip, port=5555, timeout=1.5):
    """Cek cepat apakah port terbuka via TCP socket (menghindari adb hang jika offline)."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

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
            # Pastikan bukan localhost
            if not ip.startswith("127."):
                return ip
    return None

def main():
    print("=========================================================")
    print("       SMART SCRCPY LAUNCHER (AUTO USB / WI-FI)          ")
    print("=========================================================")

    if not os.path.exists(SCRCPY_EXE):
        print(f"[!] File scrcpy.exe tidak ditemukan di: {SCRCPY_DIR}")
        input("Tekan Enter untuk keluar...")
        return

    config = load_config()
    last_ip = config.get("last_wifi_ip", "")

    usb_devices, tcp_devices = get_connected_devices()

    # KASUS 1: Perangkat USB tercolok
    if usb_devices:
        usb_dev = usb_devices[0]
        print(f"[*] Terdeteksi perangkat USB : {usb_dev}")
        print("[*] Memeriksa status Wi-Fi HP...")

        wifi_ip = detect_wifi_ip(usb_dev)
        wireless_ready = False

        if wifi_ip:
            print(f"[+] Wi-Fi HP aktif. IP terdeteksi: {wifi_ip}")
            # Simpan IP ke config.json agar selalu diingat
            if wifi_ip != last_ip:
                config["last_wifi_ip"] = wifi_ip
                save_config(config)

            # Coba aktifkan ADB TCPIP 5555
            print("[*] Menyetel port ADB nirkabel ke 5555...")
            run_cmd(f"adb -s {usb_dev} tcpip 5555", timeout=3)
            time.sleep(1)

            # Verifikasi apakah PC bisa menjangkau IP HP di port 5555
            if is_port_reachable(wifi_ip, 5555, timeout=1.5):
                print(f"[*] Mengoneksikan ADB ke {wifi_ip}:5555...")
                run_cmd(f"adb connect {wifi_ip}:5555", timeout=3)
                wireless_ready = True
            else:
                print(f"[-] Port {wifi_ip}:5555 tidak merespons (beda Wi-Fi / AP Isolation).")
        else:
            print("[*] Wi-Fi HP tidak aktif / tidak terhubung ke Wi-Fi lokal.")

        # Eksekusi Scrcpy
        if wireless_ready:
            print("\n[V] MODE NIRKABEL AKTIF!")
            print("[!] KABEL USB SEKARANG SUDAH BISA DICABUT KAPAN SAJA!")
            print(f"[*] Membuka SCRCPY nirkabel ({wifi_ip}:5555)...")
            subprocess.Popen([SCRCPY_EXE, "-s", f"{wifi_ip}:5555"], cwd=SCRCPY_DIR)
        else:
            print(f"\n[*] Membuka SCRCPY langsung via koneksi USB ({usb_dev})...")
            subprocess.Popen([SCRCPY_EXE, "-s", usb_dev], cwd=SCRCPY_DIR)
            print("[V] SCRCPY berhasil dibuka via USB.")

        time.sleep(1.5)
        return

    # KASUS 2: Tidak ada USB, cek perangkat TCP/IP yang sudah aktif
    if tcp_devices:
        tcp_dev = tcp_devices[0]
        print(f"[*] Menggunakan koneksi ADB nirkabel aktif: {tcp_dev}")
        subprocess.Popen([SCRCPY_EXE, "-s", tcp_dev], cwd=SCRCPY_DIR)
        time.sleep(1.5)
        return

    # KASUS 3: Tidak ada USB, coba hubungkan ke last_wifi_ip yang tersimpan
    if last_ip:
        print(f"[*] Tidak ada kabel USB. Memeriksa IP terakhir yang diingat: {last_ip}")
        if is_port_reachable(last_ip, 5555, timeout=1.5):
            print(f"[*] Menghubungkan ADB ke {last_ip}:5555...")
            run_cmd(f"adb connect {last_ip}:5555", timeout=3)
            subprocess.Popen([SCRCPY_EXE, "-s", f"{last_ip}:5555"], cwd=SCRCPY_DIR)
            print("[V] SCRCPY berhasil dibuka via Wi-Fi.")
            time.sleep(1.5)
            return
        else:
            print(f"[-] IP {last_ip}:5555 tidak dapat dijangkau dari jaringan ini.")

    # KASUS 4: Gagal total
    print("\n[!] PERANGKAT TIDAK DITEMUKAN!")
    print("1. Pastikan kabel USB sudah tercolok dari HP ke PC (USB Debugging ON), ATAU")
    print("2. Pastikan HP dan PC terhubung ke jaringan Wi-Fi yang sama.")
    print("=========================================================")
    input("Tekan Enter untuk keluar...")

if __name__ == "__main__":
    main()
