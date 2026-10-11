import subprocess
import re
import sys
import os
import time

def run_cmd(cmd, timeout=10):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip() if e.output else ""
    except Exception as ex:
        return str(ex)

def check_shizuku_status():
    """Mengecek apakah Shizuku (rish) aktif dan dapat digunakan di Termux."""
    env = os.environ.copy()
    env["RISH_APPLICATION_ID"] = "com.termux"
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    lib_path = os.path.join(prefix, "lib")
    if os.path.exists(lib_path):
        env["LD_LIBRARY_PATH"] = f"{lib_path}:{env.get('LD_LIBRARY_PATH', '')}"

    try:
        res = subprocess.run(
            ["rish", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env
        )
        if res.returncode == 0 and "uid=2000" in res.stdout:
            return True, res.stdout.strip()
    except Exception:
        pass
    return False, ""

def get_port_via_getprop():
    print("[*] Mengecek properti sistem Android (getprop)...")
    port = run_cmd("getprop service.adb.tls.port")
    if port and port.isdigit() and int(port) > 0:
        return port
    port_tcp = run_cmd("getprop service.adb.tcp.port")
    if port_tcp and port_tcp.isdigit() and int(port_tcp) > 0:
        return port_tcp
    return None

def get_port_via_nmap():
    print("[*] Memindai port ADB Wireless via NMAP (30000-50000)...")
    out = run_cmd("nmap -p 30000-50000 localhost")
    open_ports = re.findall(r"(\d+)/tcp\s+open", out)
    return open_ports

def check_adb_devices():
    out = run_cmd("adb devices")
    # Jika sudah ada "localhost:PORT device" berarti sudah konek
    if ("localhost:" in out or "127.0.0.1:" in out) and "device" in out and "offline" not in out:
        return True, out
    lines = [l for l in out.splitlines() if l.strip() and not l.startswith("List") and not l.startswith("*")]
    active_devs = [l for l in lines if "\tdevice" in l or " device" in l]
    if active_devs:
        return True, out
    return False, out

def main():
    print("=========================================================")
    print("      KONEKSI ADB & DETEKSI OTOMATIS RUNTIME TERMUX       ")
    print("=========================================================")

    # 1. Cek Shizuku (rish)
    shizuku_ok, shizuku_id = check_shizuku_status()
    if shizuku_ok:
        print("[+] Shizuku (rish) TERDETEKSI & AKTIF!")
        print(f"    Status Hak Akses: {shizuku_id}")
        print("[*] Catatan: Anda juga bisa menjalankan ADB Wireless di bawah ini.")
        print("---------------------------------------------------------")

    # 2. Cek apakah ADB Server aktif & sudah terkoneksi
    run_cmd("adb start-server")
    is_connected, dev_out = check_adb_devices()
    if is_connected:
        print("[+] Perangkat ADB sudah terkoneksi dengan sukses!")
        print(dev_out)
        print("=========================================================")
        sys.exit(0)

    ports_to_try = []

    # 3. Coba deteksi via getprop
    fast_port = get_port_via_getprop()
    if fast_port:
        print(f"[+] Ditemukan port ADB aktif dari sistem: {fast_port}")
        ports_to_try.append(fast_port)
    else:
        print("[-] Port tidak ditemukan di getprop (Kebijakan OS Android modern).")

    # 4. Coba via pemindaian Nmap
    if not ports_to_try:
        ports = get_port_via_nmap()
        if ports:
            print(f"[+] Ditemukan {len(ports)} port terbuka: {', '.join(ports)}")
            ports_to_try.extend(ports)

    # 5. Eksekusi koneksi otomatis jika ada port terdeteksi
    berhasil = False
    for p in ports_to_try:
        print(f"[*] Menghubungkan ke localhost:{p} ...")
        res = run_cmd(f"adb connect localhost:{p}")
        print(f"    > {res}")
        if "connected" in res.lower() and "failed" not in res.lower():
            berhasil = True
            break

    # 6. Jika belum berhasil, sediakan opsi input manual
    if not berhasil:
        print("---------------------------------------------------------")
        print("[!] Port tidak ditemukan secara otomatis.")
        print("    Buka Pengaturan HP -> Opsi Pengembang -> Proses Debug Nirkabel.")
        print("    Lihat 'Alamat IP & Port' (misal: 192.168.1.X:39485)")
        print("---------------------------------------------------------")
        try:
            manual_port = input("Masukkan PORT Wireless Debugging (atau tekan Enter untuk batal): ").strip()
            if manual_port and manual_port.isdigit():
                print(f"[*] Menghubungkan ke localhost:{manual_port} ...")
                res = run_cmd(f"adb connect localhost:{manual_port}")
                print(f"    > {res}")
                if "connected" in res.lower() and "failed" not in res.lower():
                    berhasil = True
        except (KeyboardInterrupt, EOFError):
            print("\nDibatalkan.")

    print("=========================================================")
    if berhasil:
        print("[+] SUKSES! Perangkat ADB berhasil terhubung.")
        print("[+] Sekarang Anda bisa menjalankan:")
        print("    bash run.sh")
    else:
        print("[-] BELUM TERHUBUNG!")
        print("Tips Pairing (Android 11+):")
        print("1. Buka Pengaturan -> Opsi Developer -> Proses Debug Nirkabel.")
        print("2. Split Screen layar HP antara Pengaturan dan Termux.")
        print("3. Klik 'Pasangkan perangkat dengan kode penyandingan'.")
        print("4. Di Termux jalankan perintah:")
        print("   adb pair localhost:<PORT_PAIRING>")
        print("   Lalu masukkan 6 digit kode sandinya.")
        print("5. Setelah itu sambungkan dengan: adb connect localhost:<PORT_UTAMA>")
    print("=========================================================")

if __name__ == "__main__":
    main()
