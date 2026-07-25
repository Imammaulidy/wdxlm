import subprocess
import re
import sys
import time

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()

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
    print("[*] Mengecek via pemindaian port NMAP (mencari port 30000-50000)...")
    out = run_cmd("nmap -p 30000-50000 localhost")
    open_ports = re.findall(r"(\d+)/tcp\s+open", out)
    return open_ports

def check_adb_devices():
    out = run_cmd("adb devices")
    # Jika sudah ada "localhost:PORT device" berarti sudah konek
    if "localhost:" in out and "device" in out and "offline" not in out:
        return True
    return False

def main():
    print("=========================================================")
    print("         AUTO-CONNECT ADB WIRELESS (TERMUX)              ")
    print("=========================================================")
    
    # Start server ADB agar siap
    run_cmd("adb start-server")
    
    if check_adb_devices():
        print("[!] ADB sudah terkoneksi dengan perangkat!")
        print(run_cmd("adb devices"))
        sys.exit(0)

    ports_to_try = []
    
    # 1. Coba cara cepat (getprop)
    fast_port = get_port_via_getprop()
    if fast_port:
        print(f"[+] Ditemukan port ADB aktif: {fast_port}")
        ports_to_try.append(fast_port)
    else:
        print("[-] Tidak bisa mendapatkan port via getprop (Dibatasi oleh OS Android baru).")
        
    # 2. Jika gagal atau tidak ketemu, pakai Nmap
    if not ports_to_try:
        ports = get_port_via_nmap()
        if ports:
            print(f"[+] Ditemukan {len(ports)} port yang terbuka: {', '.join(ports)}")
            ports_to_try.extend(ports)
        else:
            print("[-] Tidak ada port terbuka. Pastikan 'Proses Debug Nirkabel' sudah dihidupkan!")
            sys.exit(1)
            
    # Eksekusi koneksi
    berhasil = False
    for p in ports_to_try:
        print(f"[*] Mencoba koneksi ke localhost:{p} ...")
        res = run_cmd(f"adb connect localhost:{p}")
        print(f"    > {res}")
        if "connected" in res.lower() and "failed" not in res.lower():
            berhasil = True
            break
            
    print("=========================================================")
    if berhasil:
        print("SUKSES! Perangkat berhasil dikoneksikan.")
        print("Anda sekarang bisa menjalankan: python wd_xlm.py")
    else:
        print("GAGAL KONEK!")
        print("Jika diminta pairing (Android 11+), lakukan Split Screen:")
        print("1. Buka Pengaturan -> Opsi Developer -> Proses Debug Nirkabel.")
        print("2. Split screen dengan Termux.")
        print("3. Klik 'Pasangkan perangkat dengan kode penyandingan'.")
        print("4. Di Termux ketik: adb pair localhost:<PORT_PAIRING>")
        print("   Lalu masukkan kode sandi Wi-Fi-nya.")
    print("=========================================================")

if __name__ == "__main__":
    main()
