import os
import json
import sys
import time

CONFIG_FILE = 'config.json'

# Deteksi apakah berjalan di Termux
IS_TERMUX = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')

# Tambahkan path folder scrcpy ke environment variables agar dikenali otomatis (hanya untuk PC)
if not IS_TERMUX:
    SCRCPY_PATH = os.path.join(os.getcwd(), "templates", "QtScrcpy-win-x64-v3.3.3")
    if os.path.exists(SCRCPY_PATH):
        os.environ["PATH"] += os.pathsep + SCRCPY_PATH

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        if os.path.exists('config.example.json'):
            import shutil
            shutil.copy('config.example.json', CONFIG_FILE)
            print("[*] config.json baru berhasil dibuat dari template otomatis!")
            time.sleep(1)
        else:
            print("Error: config.json dan config.example.json tidak ditemukan!")
            sys.exit(1)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def print_menu():
    clear_screen()
    print("=========================================================")
    print("              BOT AUTO WD XLM BITGET                     ")
    print("=========================================================")
    
    config = load_config()
    print(f"[*] Address Saat Ini : {config.get('alamat_wd')[:15]}...{config.get('alamat_wd')[-5:]}")
    print(f"[*] PIN Saat Ini     : {config.get('pin')}")
    print(f"[*] Total Akun WD    : {config.get('total_akun')}")
    print("=========================================================")
    print("1. MULAI WD (OTOMATIS FULL)")
    print("2. MULAI WD MANUAL (VIA ENTER / STEP-BY-STEP)")
    print("3. GANTI ADDRESS PENERIMA DAN PIN")
    print("4. REKAM JEDA (PENYESUAIAN JEDA LAGI)")
    print("5. RESTART TERMINAL")
    if IS_TERMUX:
        print("6. KONEK ADB LOKAL (WIRELESS DEBUGGING)")
        print("7. INSTALL/UPDATE DEPENDENCIES")
        print("8. BUKA PENGATURAN DEVELOPER (Shortcut)")
    else:
        print("6. KONEK ADB & SCRCPY (KHUSUS PC)")
    print("0. EXIT")
    print("=========================================================")

def ganti_pengaturan():
    config = load_config()
    print("\n--- GANTI PENGATURAN ---")
    print("Kosongkan lalu tekan Enter jika tidak ingin mengubah data.")
    
    # Address
    baru_address = input(f"Address ({config.get('alamat_wd')}): ")
    if baru_address.strip() != "":
        config['alamat_wd'] = baru_address.strip()
        
    # PIN
    baru_pin = input(f"PIN Baru ({config.get('pin')}): ")
    if baru_pin.strip() != "":
        if not baru_pin.isdigit():
            print("ERROR: PIN harus berupa angka!")
        else:
            config['pin'] = baru_pin.strip()
            
    # Total Akun
    baru_total = input(f"Total Akun ({config.get('total_akun')}): ")
    if baru_total.strip() != "":
        if baru_total.isdigit():
            config['total_akun'] = int(baru_total.strip())
            
    save_config(config)
    print("\n[!] Pengaturan berhasil disimpan!")
    input("Tekan Enter untuk kembali ke menu...")

def konek_adb_scrcpy():
    clear_screen()
    print(">>> KONEKSI ADB & SCRCPY (PC) <<<\n")
    print("1. ADB USB/WiFi + Buka Layar (SCRCPY)")
    print("2. Hanya Buka Layar (SCRCPY)")
    print("3. Hanya Konek ADB via IP (WiFi)")
    print("4. Auto-Setup Wireless (Colok USB sebentar) - DIREKOMENDASIKAN")
    print("5. Pairing Perangkat Baru (Khusus Android 11+)")
    print("0. Batal")
    
    pil = input("\nPilih mode (0-5): ").strip()
    
    if pil == '1':
        ip = input("Masukkan IP:PORT HP (Cek Developer Options, misal 192.168.x.x:41234).\nKosongkan jika pakai kabel USB atau ingin default 192.168.2.176: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
        print("[*] Menjalankan QtScrcpy...")
        if os.name == 'nt':
            os.system('start /B QtScrcpy.exe')
        else:
            os.system('QtScrcpy &')
            
    elif pil == '2':
        print("[*] Menjalankan QtScrcpy...")
        if os.name == 'nt':
            os.system('start /B QtScrcpy.exe')
        else:
            os.system('QtScrcpy &')
            
    elif pil == '3':
        ip = input("Masukkan IP:PORT HP [Tekan Enter untuk default 192.168.2.176]: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
            
    elif pil == '4':
        print("\n=== AUTO-SETUP WIRELESS ===")
        print("Syarat: Sambungkan HP ke PC pakai Kabel USB sebentar saja.")
        input("Tekan Enter jika KABEL USB SUDAH TERSAMBUNG...")
        
        print("\n[*] Membersihkan koneksi lama dan menyetel port USB ke 5555...")
        os.system('adb disconnect')
        os.system('adb -d tcpip 5555')
        
        print("\n[!] SUKSES! Sekarang CABUT KABEL USB Anda.")
        ip = input("Masukkan IP HP Anda [Tekan Enter untuk default: 192.168.2.176]: ").strip()
        if not ip:
            ip = "192.168.2.176"
        if ip:
            print(f"[*] Mencoba koneksi Nirkabel ke {ip}:5555...")
            os.system(f'adb connect {ip}:5555')
            
    elif pil == '5':
        print("\n=== PAIRING ANDROID 11+ ===")
        print("1. Buka Opsi Developer -> Proses Debug Nirkabel.")
        print("2. Klik 'Pasangkan perangkat dengan kode penyandingan'.")
        print("3. Lihat Alamat IP & Port, dan 6 digit Kode.")
        ip_port = input("Masukkan IP:PORT Pairing (misal 192.168.x.x:35612): ").strip()
        code = input("Masukkan 6 Digit Kode Pairing: ").strip()
        if ip_port and code:
            os.system(f'adb pair {ip_port} {code}')
            
    if pil in ['1', '2', '3', '4', '5']:
        input("\nProses selesai. Tekan Enter untuk kembali ke menu...")

def main():
    while True:
        print_menu()
        if IS_TERMUX:
            pilihan = input("Pilih menu (0-8): ").strip()
        else:
            pilihan = input("Pilih menu (0-6): ").strip()
        
        if pilihan == '1':
            clear_screen()
            print(">>> MENJALANKAN WD OTOMATIS <<<\n")
            os.system('python wd_xlm.py')
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '2':
            clear_screen()
            print(">>> MENJALANKAN WD MANUAL (STEP-BY-STEP) <<<\n")
            os.system('python wd_xlm.py --manual')
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '3':
            ganti_pengaturan()
            
        elif pilihan == '4':
            clear_screen()
            print(">>> MASUK KE MODE REKAM JEDA <<<\n")
            os.system('python tester.py')
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '5':
            clear_screen()
            print("[*] Merestart ulang sistem Menu Utama...")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)
            
        elif pilihan == '6':
            if IS_TERMUX:
                clear_screen()
                print("=========================================================")
                print("SYARAT: Nyalakan 'Proses Debug Nirkabel' (Wireless Debugging)")
                print("di Pengaturan Developer HP Anda sebelum melanjutkan.")
                print("=========================================================")
                os.system('python termux/konek_adb.py')
                print("\n")
                input("Tekan Enter untuk kembali ke menu...")
            else:
                konek_adb_scrcpy()
                
        elif pilihan == '7' and IS_TERMUX:
            clear_screen()
            os.system('bash setup.sh')
            print("\n")
            input("Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '8' and IS_TERMUX:
            clear_screen()
            print("[*] Membuka Pengaturan Developer di HP Anda...")
            os.system('am start -a android.settings.APPLICATION_DEVELOPMENT_SETTINGS')
            print("\n")
            input("Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '0':
            clear_screen()
            print("Keluar dari program. Terima kasih!")
            sys.exit(0)
            
        else:
            print("Pilihan tidak valid!")
            time.sleep(1)

if __name__ == "__main__":
    import time
    main()
