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

    # =========================================================================
    # KASUS 1: PRIORITAS TERTINGGI - PERANGKAT USB TERCOLOK
    # =========================================================================
    if usb_devices:
        usb_dev = usb_devices[0]
        print(f"[+] Terdeteksi perangkat USB : {usb_dev}")
        print("[*] MEMPRIORITASKAN KONEKSI KABEL USB (Ultra-Smooth 120 FPS, Zero Latency)...")

        # Catat IP Wi-Fi untuk referensi tanpa me-restart daemon adb
        try:
            wifi_ip = detect_wifi_ip(usb_dev)
            if wifi_ip:
                if wifi_ip != last_ip:
                    config["last_wifi_ip"] = wifi_ip
                    save_config(config)
                print(f"[*] Info Wi-Fi HP: {wifi_ip}:5555 tersimpan.")
        except Exception:
            pass

        print(f"[*] Membuka SCRCPY via USB ({usb_dev}) dengan layar fisik dimatikan (120 FPS)...")
        try:
            p = subprocess.Popen([SCRCPY_EXE, "-s", usb_dev, "-S", "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
            time.sleep(1.0)
            if p.poll() is not None and p.poll() != 0:
                print("[-] Fallback: Membuka SCRCPY tanpa flag -S...")
                p = subprocess.Popen([SCRCPY_EXE, "-s", usb_dev, "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
                time.sleep(1.0)

            if p.poll() is None:
                print("[V] SCRCPY aktif di layar monitor Anda. Menyembunyikan terminal...")
                hide_console()
                p.wait()
                return
            else:
                print(f"[!] Scrcpy gagal dimulai (kode keluar: {p.poll()}).")
                input("\nTekan Enter untuk keluar...")
                return
        except Exception as e:
            print(f"[!] Gagal menjalankan scrcpy: {e}")
            input("\nTekan Enter untuk keluar...")
        return

    # =========================================================================
    # KASUS 2: TIDAK ADA KABEL USB -> CEK KONEKSI TCP/IP AKTIF
    # =========================================================================
    for tcp_dev in tcp_devices:
        ip_part = tcp_dev.split(":")[0]
        port_part = int(tcp_dev.split(":")[1]) if ":" in tcp_dev else 5555
        if is_port_reachable(ip_part, port_part, timeout=1.0):
            print(f"[*] Terdeteksi koneksi nirkabel aktif: {tcp_dev}")
            print(f"[*] Membuka SCRCPY via Wi-Fi ({tcp_dev}) dengan layar fisik dimatikan (120 FPS)...")
            try:
                p = subprocess.Popen([SCRCPY_EXE, "-s", tcp_dev, "-S", "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
                time.sleep(1.0)
                if p.poll() is not None and p.poll() != 0:
                    p = subprocess.Popen([SCRCPY_EXE, "-s", tcp_dev, "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
                    time.sleep(1.0)

                if p.poll() is None:
                    print("[V] SCRCPY nirkabel aktif di layar monitor Anda. Menyembunyikan terminal...")
                    hide_console()
                    p.wait()
                    return
                else:
                    print(f"[!] Scrcpy nirkabel berhenti (kode keluar: {p.poll()}).")
                    input("\nTekan Enter untuk keluar...")
                    return
            except Exception as e:
                print(f"[!] Gagal membuka scrcpy: {e}")
        else:
            print(f"[-] Stale socket terdeteksi di {tcp_dev}, memutuskan...")
            run_cmd(f"adb disconnect {tcp_dev}", timeout=2)

    # =========================================================================
    # KASUS 3: TIDAK ADA USB & BELUM KONEK TCP -> COBA HUBUNGKAN KE LAST_WIFI_IP
    # =========================================================================
    if last_ip:
        print(f"[*] Mencari perangkat pada IP Wi-Fi terakhir yang diingat: {last_ip}:5555...")
        if is_port_reachable(last_ip, 5555, timeout=1.5):
            print(f"[*] Menghubungkan ADB ke {last_ip}:5555...")
            run_cmd(f"adb connect {last_ip}:5555", timeout=3)
            print(f"[*] Membuka SCRCPY via Wi-Fi ({last_ip}:5555)...")
            try:
                p = subprocess.Popen([SCRCPY_EXE, "-s", f"{last_ip}:5555", "-S", "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
                time.sleep(1.0)
                if p.poll() is not None and p.poll() != 0:
                    p = subprocess.Popen([SCRCPY_EXE, "-s", f"{last_ip}:5555", "-w", "--max-fps=120"], cwd=SCRCPY_DIR)
                    time.sleep(1.0)

                if p.poll() is None:
                    print("[V] SCRCPY berhasil dibuka via Wi-Fi. Menyembunyikan terminal...")
                    hide_console()
                    p.wait()
                    return
                else:
                    print(f"[!] Scrcpy Wi-Fi berhenti (kode keluar: {p.poll()}).")
                    input("\nTekan Enter untuk keluar...")
                    return
            except Exception as e:
                print(f"[!] Gagal membuka scrcpy: {e}")
        else:
            print(f"[-] IP {last_ip}:5555 tidak dapat dijangkau dari jaringan ini.")

    # =========================================================================
    # KASUS 4: PERANGKAT TIDAK DITEMUKAN (ANTI-MENTAL DENGAN DIAGNOSTIK)
    # =========================================================================
    print("\n=========================================================")
    print("           [!] PERANGKAT ANDROID TIDAK DITEMUKAN         ")
    print("=========================================================")
    print("1. Pastikan kabel USB tercolok dari HP ke PC (USB Debugging ON).")
    print("2. Jika menggunakan mode nirkabel, pastikan HP dan PC terhubung ke Wi-Fi yang sama.")
    print("3. Jika port ADB terkunci/error, jalankan Menu [7] di START BOT.bat untuk reset total.")
    print("=========================================================")
    input("\nTekan Enter untuk keluar...")

if __name__ == "__main__":
    main()

