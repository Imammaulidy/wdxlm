import os
import sys
import json
import re
import subprocess
import time

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, ".."))
CONFIG_FILE = os.path.join(CORE_DIR, "config.json")
SCRCPY_DIR = os.path.join(CORE_DIR, "scrcpy-win64-v3.3.4")
SCRCPY_EXE = os.path.join(SCRCPY_DIR, "scrcpy.exe")

# Tambahkan scrcpy ke PATH
if SCRCPY_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = SCRCPY_DIR + os.pathsep + os.environ.get("PATH", "")

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
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

def get_usb_device():
    out = run_cmd("adb devices")
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device" and ":" not in parts[0]:
            return parts[0]
    return None

def detect_device_wifi_ip():
    commands = [
        "adb -d shell ip -f inet addr show wlan0",
        "adb -d shell ip route",
        "adb shell ip -f inet addr show wlan0",
        "adb shell ip route"
    ]
    for cmd in commands:
        out = run_cmd(cmd)
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m and not m.group(1).startswith("127."):
            return m.group(1)
        m = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", out)
        if m and not m.group(1).startswith("127."):
            return m.group(1)
    return None

def main():
    print("=========================================================")
    print("       AUTO-SWITCH USB KE ADB WI-FI & SCRCPY             ")
    print("=========================================================")

    if not os.path.exists(SCRCPY_EXE):
        print(f"[!] File scrcpy.exe tidak ditemukan di: {SCRCPY_DIR}")
        input("Tekan Enter untuk keluar...")
        return

    config = load_config()
    last_ip = config.get("last_wifi_ip", "")

    # 1. Cek apakah ada HP tersambung lewat USB
    usb_dev = get_usb_device()
    target_ip = None

    if usb_dev:
        print(f"[*] Terdeteksi perangkat USB: {usb_dev}")
        print("[*] Membaca IP Wi-Fi HP secara otomatis...")
        detected_ip = detect_device_wifi_ip()
        if detected_ip:
            target_ip = detected_ip
            print(f"[+] IP Wi-Fi HP berhasil dideteksi: {target_ip}")
            # Simpan IP ke config.json agar selalu diingat
            config["last_wifi_ip"] = target_ip
            save_config(config)

            print("[*] Menyetel port ADB nirkabel ke 5555...")
            run_cmd("adb -d tcpip 5555")
            time.sleep(1)

            print(f"[*] Mengoneksikan ADB ke {target_ip}:5555...")
            run_cmd(f"adb connect {target_ip}:5555")
            print("[V] SUKSES! Perangkat terhubung via Wi-Fi.")
            print("[!] KABEL USB SEKARANG SUDAH BISA DICABUT KAPAN SAJA!")
        else:
            print("[-] Gagal mendeteksi IP Wi-Fi HP (pastikan HP sudah tersambung ke Wi-Fi).")
    else:
        print("[*] Tidak ada perangkat USB yang terdeteksi.")
        if last_ip:
            print(f"[*] Menggunakan IP Wi-Fi terakhir yang diingat: {last_ip}")
            print(f"[*] Mencoba mengoneksikan ke {last_ip}:5555...")
            run_cmd(f"adb connect {last_ip}:5555")
            target_ip = last_ip

    # 2. Jalankan SCRCPY
    scrcpy_cmd = [SCRCPY_EXE]
    if target_ip:
        scrcpy_cmd.extend(["-s", f"{target_ip}:5555"])
        print(f"[*] Membuka SCRCPY pada koneksi nirkabel ({target_ip}:5555)...")
    else:
        print("[*] Membuka SCRCPY...")

    # Buka scrcpy di background
    subprocess.Popen(scrcpy_cmd, cwd=SCRCPY_DIR)
    print("\n[V] SCRCPY berhasil dibuka. Layar akan tetap aktif meskipun kabel USB dicabut!")
    time.sleep(2)

if __name__ == "__main__":
    main()
