import os
import json
import sys
import time

CONFIG_FILE = 'config.json'

# Tambahkan path folder scrcpy ke environment variables agar dikenali otomatis
SCRCPY_PATH = os.path.join(os.getcwd(), "templates", "scrcpy-win64-v3.3.3")
if os.path.exists(SCRCPY_PATH):
    os.environ["PATH"] += os.pathsep + SCRCPY_PATH

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("Error: config.json tidak ditemukan!")
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
    print("1. MULAI WD")
    print("2. GANTI ADDRESS PENERIMA DAN PIN")
    print("3. REKAM JEDA (PENYESUAIAN JEDA LAGI)")
    print("4. RESTART TERMINAL")
    print("5. KONEK ADB & SCRCPY (KHUSUS PC)")
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
    print("0. Batal")
    
    pil = input("\nPilih mode (0-3): ").strip()
    
    if pil == '1':
        ip = input("Masukkan IP:PORT HP (Cek Developer Options, misal 192.168.x.x:41234).\nKosongkan jika pakai kabel USB: ").strip()
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
        print("[*] Menjalankan SCRCPY...")
        if os.name == 'nt':
            os.system('start /B scrcpy')
        else:
            os.system('scrcpy &')
            
    elif pil == '2':
        print("[*] Menjalankan SCRCPY...")
        if os.name == 'nt':
            os.system('start /B scrcpy')
        else:
            os.system('scrcpy &')
            
    elif pil == '3':
        ip = input("Masukkan IP:PORT HP (misal 192.168.x.x:41234): ").strip()
        if ip:
            print(f"[*] Mencoba koneksi ke {ip}...")
            os.system(f'adb connect {ip}')
            
    if pil in ['1', '2', '3']:
        input("\nProses selesai. Tekan Enter untuk kembali ke menu...")

def main():
    while True:
        print_menu()
        pilihan = input("Pilih menu (0-5): ").strip()
        
        if pilihan == '1':
            clear_screen()
            print(">>> MENJALANKAN WD OTOMATIS <<<\n")
            os.system('python wd_xlm.py')
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '2':
            ganti_pengaturan()
            
        elif pilihan == '3':
            clear_screen()
            print(">>> MASUK KE MODE REKAM JEDA <<<\n")
            os.system('python tester.py')
            print("\n")
            input("Selesai. Tekan Enter untuk kembali ke menu...")
            
        elif pilihan == '4':
            # Hanya clear screen dan loop lagi
            continue
            
        elif pilihan == '5':
            konek_adb_scrcpy()
            
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
