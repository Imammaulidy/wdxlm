import os
import sys
import time
import socket
import subprocess
import shutil

# Root & Core Directory Setup
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CORE_DIR = os.path.abspath(os.path.dirname(__file__))

if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)

from server import get_local_machine_ip, PUBLIC_DOMAIN, PORT
from screen_manager import get_detailed_connected_devices, record_and_apply_bot_screen

# ANSI Color Codes
G = "\033[92m"  # Green
Y = "\033[93m"  # Yellow
C = "\033[96m"  # Cyan
R = "\033[91m"  # Red
W = "\033[97m"  # Bright White
DIM = "\033[90m"# Gray
RST = "\033[0m" # Reset

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

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
                    return 'enter'
                if ch_str:
                    print(ch_str)
                    return ch_str
            except Exception:
                pass
    else:
        try:
            return input().strip()
        except (KeyboardInterrupt, EOFError):
            return "0"

def wait_any_key(msg: str = "\n Tekan sembarang tombol untuk kembali ke menu..."):
    get_key_press(f"{Y}{msg}{RST}")

def run_cmd(cmd_list, timeout=15):
    """Menjalankan perintah sistem secara aman dengan fallback npx."""
    cmd_str = " ".join(cmd_list) if isinstance(cmd_list, list) else cmd_list
    try:
        r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout, cwd=PROJECT_ROOT)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def is_pm2_running(app_name="bitget-server") -> bool:
    """Mengecek apakah proses PM2 sedang online."""
    code, out, _ = run_cmd("pm2 jlist")
    if code != 0:
        code, out, _ = run_cmd("npx pm2 jlist")
    if code == 0 and out:
        try:
            import json
            apps = json.loads(out)
            for a in apps:
                if a.get("name") == app_name and a.get("pm2_env", {}).get("status") == "online":
                    return True
        except Exception:
            return app_name in out and "online" in out
    return False

def check_port_listening(port=PORT) -> bool:
    """Mengecek apakah port web sedang aktif / listening."""
    code, out, _ = run_cmd(f'netstat -ano -p tcp | findstr ":{port}.*LISTENING"')
    return bool(code == 0 and out)

def free_port(port=PORT):
    """Menghentikan proses apapun yang mengunci port tertentu."""
    if os.name == 'nt':
        try:
            out = subprocess.check_output(f'netstat -ano -p tcp | findstr ":{port}.*LISTENING"', shell=True, text=True)
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[-1].isdigit():
                    pid = int(parts[-1])
                    if pid > 0:
                        subprocess.run(f"taskkill /F /PID {pid} /T >nul 2>&1", shell=True)
        except Exception:
            pass

def open_browser(url: str):
    """Membuka browser bawaan ke alamat dashboard."""
    if os.name == 'nt':
        os.system(f'start "" "{url}"')
    else:
        try:
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def print_header(local_ip: str, public_domain: str, devices_list):
    local_url = f"http://{local_ip}:{PORT}"
    pm2_online = is_pm2_running("bitget-server")
    port_active = check_port_listening(PORT)

    pm2_badge = f"{G}ONLINE (24/7 Away Mode){RST}" if pm2_online else f"{R}OFFLINE{RST}"
    port_badge = f"{G}AKTIF (: {PORT}){RST}" if port_active else f"{DIM}TERTUTUP{RST}"
    dev_str = ", ".join([f"{d['model']} ({d['serial']})" for d in devices_list]) if devices_list else f"{DIM}Tidak Ada HP Terhubung{RST}"

    print(f"{G}========================================================={RST}")
    print(f"{W}  BITGET WALLET & BOT WEB DASHBOARD CONTROLLER (PORT {PORT}) {RST}")
    print(f"{G}========================================================={RST}")
    print(f"[*] {C}Akses Local LAN{RST}    : {W}{local_url}{RST}")
    print(f"[*] {C}Domain Cloudflare{RST}  : {W}https://{public_domain}{RST}")
    print(f"[*] {C}Status PM2 24/7{RST}    : {pm2_badge}")
    print(f"[*] {C}Status Port {PORT}{RST}     : {port_badge}")
    print(f"[*] {C}Target Device ADB{RST}  : {W}{dev_str}{RST} ({len(devices_list)} HP)")
    print(f"{G}========================================================={RST}")
    print(f" [1] JALANKAN WEB DASHBOARD (LANGSUNG / FOREGROUND CMD)")
    print(f" [2] JALANKAN DENGAN PM2 (BACKGROUND 24 JAM SAAT LAYAR MATI)")
    print(f" [3] LIHAT STATUS & LOG PM2 (pm2 status & logs)")
    print(f" [4] RESTART SERVICE PM2 (Segarkan Server & Tunnel)")
    print(f" [5] STOP SERVER / MATIKAN PM2 & BEBASKAN PORT {PORT}")
    print(f" [W] BUKA DASHBOARD DI BROWSER ({local_url})")
    print(f" [R] RESTART ADB SERVER & REFRESH KONEKSI HP")
    print(f" [0] EXIT / KELUAR")
    print(f"{G}========================================================={RST}")

def main():
    if os.name == 'nt':
        os.system('color 0A')
        os.system(f'title Bitget Wallet Tools — Web Dashboard Controller (Port {PORT})')

    local_ip = get_local_machine_ip()
    local_url = f"http://{local_ip}:{PORT}"

    while True:
        try:
            devices = get_detailed_connected_devices()
        except Exception:
            devices = []

        clear_screen()
        print_header(local_ip, PUBLIC_DOMAIN, devices)

        try:
            choice = get_key_press(f" {W}Masukkan pilihan Anda [0-5 / W / R] (Tekan Tombol Langsung): {RST}").strip().lower()
        except KeyboardInterrupt:
            break

        if choice == '1':
            # Foreground CMD
            clear_screen()
            print(f"{G}========================================================={RST}")
            print(f"{W}  MENJALANKAN WEB DASHBOARD (MODE FOREGROUND CMD)         {RST}")
            print(f"{G}========================================================={RST}")
            print(f"  Akses Local LAN  : {W}{local_url}{RST}")
            print(f"  Domain Publik    : {W}https://{PUBLIC_DOMAIN}{RST}")
            print(f"  Tekan {Y}Ctrl + C{RST} untuk menghentikan server dan kembali ke menu.")
            print(f"{G}========================================================={RST}\n")

            # Buka browser
            open_browser(local_url)

            # Format layar HP terkoneksi
            for d in devices:
                record_and_apply_bot_screen(serial=d["serial"], silent=True)

            server_script = os.path.join(CORE_DIR, 'server.py')
            try:
                subprocess.run([sys.executable, server_script], cwd=PROJECT_ROOT)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"\n{R}[!] Terjadi kesalahan pada server: {e}{RST}")
            
            wait_any_key("\n Server telah berhenti. Tekan sembarang tombol untuk kembali...")

        elif choice == '2':
            # PM2 Background
            clear_screen()
            print(f"{G}========================================================={RST}")
            print(f"{W}  MENYALAKAN SERVER BACKGROUND DENGAN PM2 (PORT {PORT})     {RST}")
            print(f"{G}========================================================={RST}\n")
            print("[*] Mengaktifkan proteksi Windows Anti-Sleep (Away Mode)...")
            run_cmd("powercfg /change standby-timeout-ac 0")
            run_cmd("powercfg /change hibernate-timeout-ac 0")

            print(f"[*] Memeriksa & membebaskan Port {PORT}...")
            free_port(PORT)

            print("[*] Mendaftarkan layanan bitget-server ke PM2...")
            ecosystem_file = os.path.join(CORE_DIR, 'ecosystem.config.js')
            run_cmd("pm2 delete bitget-server")
            run_cmd("npx pm2 delete bitget-server")
            
            code, out, err = run_cmd(f'pm2 start "{ecosystem_file}"')
            if code != 0:
                code, out, err = run_cmd(f'npx pm2 start "{ecosystem_file}"')
            
            run_cmd("pm2 save")
            run_cmd("npx pm2 save")

            print(f"\n{G}[SUKSES] Server telah berhasil dijalankan di latar belakang!{RST}")
            print(f" [+] URL LAN      : {W}{local_url}{RST}")
            print(f" [+] Domain Publik: {W}https://{PUBLIC_DOMAIN}{RST}")
            print(f" [+] Proteksi 24/7: {G}AKTIF (Layar mati / laptop ditutup tetap jalan){RST}")

            print(f"\n[*] Membuka browser ke dashboard...")
            time.sleep(1)
            open_browser(local_url)

            wait_any_key("\n Tekan sembarang tombol untuk kembali ke menu utama...")

        elif choice == '3':
            # Lihat Status & Log PM2
            clear_screen()
            print(f"{G}========================================================={RST}")
            print(f"{W}  STATUS & MONITOR PM2 (bitget-server)                   {RST}")
            print(f"{G}========================================================={RST}\n")
            code, out, _ = run_cmd("pm2 status bitget-server")
            if code != 0:
                code, out, _ = run_cmd("npx pm2 status bitget-server")
            print(out if out else f"{R}Tidak ada data status PM2.{RST}")

            print(f"\n{G}========================================================={RST}")
            print(f"{W}  30 BARIS LOG TERAKHIR BITGET SERVER                    {RST}")
            print(f"{G}========================================================={RST}\n")
            code, out, _ = run_cmd("pm2 logs bitget-server --lines 30 --nostream")
            if code != 0:
                code, out, _ = run_cmd("npx pm2 logs bitget-server --lines 30 --nostream")
            print(out if out else f"{DIM}(Belum ada log server){RST}")

            wait_any_key()

        elif choice == '4':
            # Restart PM2
            clear_screen()
            print(f"{G}========================================================={RST}")
            print(f"{W}  MERESTART LAYANAN BITGET SERVER DI PM2                 {RST}")
            print(f"{G}========================================================={RST}\n")
            print("[*] Mengirim perintah restart ke PM2...")
            code, out, _ = run_cmd("pm2 restart bitget-server")
            if code != 0:
                code, out, _ = run_cmd("npx pm2 restart bitget-server")
            print(out)
            print(f"\n{G}[V] Layanan bitget-server berhasil direstart!{RST}")
            wait_any_key()

        elif choice == '5':
            # Stop PM2
            clear_screen()
            print(f"{G}========================================================={RST}")
            print(f"{W}  MENGHENTIKAN LAYANAN BITGET SERVER                     {RST}")
            print(f"{G}========================================================={RST}\n")
            print("[*] Menghentikan dan menghapus bitget-server dari PM2...")
            run_cmd("pm2 stop bitget-server")
            run_cmd("npx pm2 stop bitget-server")
            run_cmd("pm2 delete bitget-server")
            run_cmd("npx pm2 delete bitget-server")
            run_cmd("pm2 save")
            run_cmd("npx pm2 save")

            print(f"[*] Membebaskan Port {PORT}...")
            free_port(PORT)

            print(f"\n{G}[+] Server dan Port {PORT} telah berhasil dihentikan.{RST}")
            wait_any_key()

        elif choice in ('w', 'browser'):
            open_browser(local_url)

        elif choice in ('r', 'restart'):
            clear_screen()
            print("[*] Merestart ADB server dan memindai ulang perangkat...")
            run_cmd("adb kill-server")
            time.sleep(1)
            run_cmd("adb start-server")
            time.sleep(1)
            wait_any_key("\n[V] ADB berhasil direstart. Tekan sembarang tombol...")

        elif choice in ('0', 'q', 'exit'):
            clear_screen()
            print(f"{G}[*] Keluar dari Controller Web Dashboard.{RST}")
            break

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        pass
