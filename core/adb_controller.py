import os
import sys
import time
import subprocess
import shutil
import re
from typing import Optional, Dict, Any, List, Tuple

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))

CLONE_APPS = {
    "dual_space": {
        "id": "dual_space",
        "name": "Dual Space",
        "package": "com.xunijun.app.gp",
        "desc": "Dual Space (v1.205)"
    },
    "multiple_app": {
        "id": "multiple_app",
        "name": "Multiple App",
        "package": "com.multipleapp.clonespace",
        "desc": "Multiple App (v1.0.7)"
    },
    "multi_app": {
        "id": "multi_app",
        "name": "Multi App",
        "package": "com.waxmoon.ma.gp",
        "desc": "Multi App (v2.5.10)"
    }
}

DEFAULT_KEYPAD_COORDS = {
    "1": {"x": 210, "y": 1735},
    "2": {"x": 540, "y": 1735},
    "3": {"x": 875, "y": 1735},
    "4": {"x": 210, "y": 1885},
    "5": {"x": 540, "y": 1885},
    "6": {"x": 875, "y": 1885},
    "7": {"x": 210, "y": 2030},
    "8": {"x": 540, "y": 2030},
    "9": {"x": 875, "y": 2030},
    "0": {"x": 540, "y": 2180}
}

class ADBController:
    """Kontroler ADB Lengkap untuk Automasi Android & Clone Apps."""

    def __init__(self, serial: Optional[str] = None):
        self.serial = serial
        self._ensure_path()

    def _ensure_path(self):
        """Memastikan binary ADB & scrcpy ada di environment PATH."""
        candidates = [
            os.path.join(PROJECT_ROOT, "core", "scrcpy-win64-v3.3.4"),
            r"C:\Users\KAGE\Desktop\scrcpy-win64-v3.3.4",
            os.path.join(os.path.expanduser("~"), "Desktop", "scrcpy-win64-v3.3.4"),
            r"C:\Users\KAGE\Desktop\PROJECT BOT IMAM\SCRIPT ADB WD XLM BITGET\core\scrcpy-win64-v3.3.4",
            r"C:\Users\KAGE\Desktop\PROJECT BOT IMAM\COINS_PAYMENT_GATEWAY\core\scrcpy-win64-v3.3.4",
        ]
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop_dir):
            for item in os.listdir(desktop_dir):
                if "scrcpy" in item.lower():
                    candidates.append(os.path.join(desktop_dir, item))

        for p in candidates:
            if os.path.exists(p) and p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

    def run(self, cmd_args: str, timeout: int = 15) -> str:
        """Menjalankan perintah ADB dengan target serial spesifik jika ada."""
        prefix = f"adb -s {self.serial} " if self.serial else "adb "
        full_cmd = prefix + cmd_args
        try:
            res = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return res.stdout.strip()
        except Exception as e:
            return ""

    def get_devices(self) -> List[str]:
        """Mendapatkan daftar device yang terhubung."""
        out = self.run("devices")
        devs = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devs.append(parts[0])
        return devs

    def check_connection(self) -> bool:
        """Mengecek apakah device aktif terhubung."""
        devs = self.get_devices()
        if not devs:
            return False
        if self.serial and self.serial not in devs:
            return False
        if not self.serial and devs:
            self.serial = devs[0]
        return True

    def force_stop_and_clear_cache(self, clone_key: str, stop_checker=None) -> bool:
        """
        1. Paksa berhenti (Force Stop) aplikasi clone & semua sub-process.
        2. Hapus Cache aplikasi internal & external tanpa menghapus data akun/slot.
        """
        if stop_checker and stop_checker():
            return False
        if clone_key not in CLONE_APPS:
            print(f"[!] Kunci clone '{clone_key}' tidak valid.")
            return False

        pkg = CLONE_APPS[clone_key]["package"]
        name = CLONE_APPS[clone_key]["name"]
        print(f"[*] [1/3] Memaksa Berhenti (Force Stop) {name} ({pkg})...")

        # Force stop package dan core/clone sub-process
        stop_cmd = f"am force-stop {pkg}; am force-stop {pkg}:core; am force-stop {pkg}:clone;"
        self.run(f"shell \"{stop_cmd}\"")
        time.sleep(1)

        if stop_checker and stop_checker():
            return False

        print(f"[*] [2/3] Membersihkan Cache {name}...")
        clean_cmd = (
            f"rm -rf /sdcard/Android/data/{pkg}/cache/*; "
            f"pm clear-cache {pkg} 2>/dev/null; "
            f"rm -rf /data/data/{pkg}/cache/* 2>/dev/null; "
            f"rm -rf /data/data/{pkg}/code_cache/* 2>/dev/null;"
        )
        self.run(f"shell \"{clean_cmd}\"")
        time.sleep(1)
        print(f"[V] Cache {name} berhasil dibersihkan.")
        return True

    def toggle_airplane_mode(self, duration_seconds: int = 3, stop_checker=None) -> bool:
        """
        Mengaktifkan Mode Pesawat (ON) selama `duration_seconds`, lalu mematikan kembali (OFF).
        Digunakan untuk reset IP jaringan seluler / koneksi baru.
        """
        if stop_checker and stop_checker():
            return False

        print(f"[*] [3/4] Mengaktifkan Mode Pesawat (Reset IP Jaringan)...")
        on_cmd = (
            "cmd connectivity airplane-mode enable; "
            "settings put global airplane_mode_on 1; "
            "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true;"
        )
        self.run(f"shell \"{on_cmd}\"")

        print(f"[*] Menunggu jeda mode pesawat ({duration_seconds} detik)...")
        for s in range(duration_seconds, 0, -1):
            if stop_checker and stop_checker():
                # Matikan kembali mode pesawat sebelum keluar agar koneksi tidak mati
                off_cmd = (
                    "cmd connectivity airplane-mode disable; "
                    "settings put global airplane_mode_on 0; "
                    "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false;"
                )
                self.run(f"shell \"{off_cmd}\"")
                print("    -> Dibatalkan oleh pengguna.")
                return False
            print(f"    -> {s}s...", end="\r", flush=True)
            time.sleep(1)
        print("    -> 0s. Selesai jeda.")

        print("[*] Mematikan Mode Pesawat (Koneksi Baru Aktif)...")
        off_cmd = (
            "cmd connectivity airplane-mode disable; "
            "settings put global airplane_mode_on 0; "
            "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false;"
        )
        self.run(f"shell \"{off_cmd}\"")
        time.sleep(2)  # Jeda 2 detik agar sinyal terhubung kembali
        print("[V] Reset Mode Pesawat selesai, koneksi jaringan disegarkan.")
        return True

    def reset_advertising_id(self, stop_checker=None) -> bool:
        """
        Mereset Google Advertising ID (GAID / ID Iklan) secara otomatis:
        1. Membuka halaman Ads Identity Settings secara langsung via Intent.
        2. Mencari dan mengetuk tombol 'Reset ID iklan'.
        3. Mencari dan mengonfirmasi tombol pop-up dialog ('Konfirmasi' / 'OK' / 'button1').
        4. Menutup kembali halaman pengaturan (Back).
        """
        if stop_checker and stop_checker():
            return False

        print("[*] [2/4] Mereset Google Advertising ID (ID Iklan)...")
        self.run("shell am start -a com.google.android.gms.adsidentity.ACTION_ADS_IDENTITY_SETTINGS")
        time.sleep(1.0)

        if stop_checker and stop_checker():
            self.keyevent(4, delay_after=0.3)
            return False

        dump_remote = "/sdcard/temp_ad_dump.xml"
        dump_local = os.path.join(CORE_DIR, ".temp_ad_dump.xml")

        tap_reset_x, tap_reset_y = 171, 678
        try:
            self.run(f"shell uiautomator dump {dump_remote}")
            self.run(f'pull {dump_remote} "{dump_local}"')
            self.run(f"shell rm -f {dump_remote}")

            if os.path.exists(dump_local):
                import xml.etree.ElementTree as ET
                tree = ET.parse(dump_local)
                if os.path.exists(dump_local):
                    os.remove(dump_local)
                for node in tree.getroot().iter("node"):
                    txt = node.attrib.get("text", "")
                    if "Reset ID iklan" in txt:
                        bounds = node.attrib.get("bounds", "")
                        m = re.findall(r"\[(\d+),(\d+)\]", bounds)
                        if len(m) == 2:
                            tap_reset_x = (int(m[0][0]) + int(m[1][0])) // 2
                            tap_reset_y = (int(m[0][1]) + int(m[1][1])) // 2
                            break
        except Exception:
            pass

        # Tap 'Reset ID iklan'
        self.tap(tap_reset_x, tap_reset_y, delay_after=0.8)

        if stop_checker and stop_checker():
            self.keyevent(4, delay_after=0.3)
            return False

        confirmed = False
        try:
            self.run(f"shell uiautomator dump {dump_remote}")
            self.run(f'pull {dump_remote} "{dump_local}"')
            self.run(f"shell rm -f {dump_remote}")

            if os.path.exists(dump_local):
                import xml.etree.ElementTree as ET
                tree = ET.parse(dump_local)
                if os.path.exists(dump_local):
                    os.remove(dump_local)
                for node in tree.getroot().iter("node"):
                    rid = node.attrib.get("resource-id", "")
                    txt = node.attrib.get("text", "").lower()
                    if rid == "android:id/button1" or txt in ("konfirmasi", "ok", "reset"):
                        bounds = node.attrib.get("bounds", "")
                        m = re.findall(r"\[(\d+),(\d+)\]", bounds)
                        if len(m) == 2:
                            bx = (int(m[0][0]) + int(m[1][0])) // 2
                            by = (int(m[0][1]) + int(m[1][1])) // 2
                            self.tap(bx, by, delay_after=0.6)
                            confirmed = True
                            break
        except Exception:
            pass

        if not confirmed:
            # Fallback koordinat tombol konfirmasi pop-up standar Android (kanan bawah dialog)
            self.tap(880, 1380, delay_after=0.6)

        # Tutup kembali halaman Setelan Iklan
        self.keyevent(4, delay_after=0.5)
        print("[V] Google Advertising ID (ID Iklan) berhasil di-reset ke identitas acak baru.")
        return True

    def launch_clone_app(self, clone_key: str, stop_checker=None) -> bool:
        """Membuka kembali aplikasi clone yang sedang digunakan."""
        if stop_checker and stop_checker():
            return False
        if clone_key not in CLONE_APPS:
            return False

        pkg = CLONE_APPS[clone_key]["package"]
        name = CLONE_APPS[clone_key]["name"]
        print(f"[*] [4/4] Membuka kembali aplikasi {name}...")
        self.run(f"shell monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
        time.sleep(2)
        print(f"[V] Aplikasi {name} berhasil dipanggil.")
        return True

    def reset_and_launch(self, clone_key: str, airplane_seconds: int = 3, stop_checker=None, reset_ad_id: bool = True) -> bool:
        """Kombinasi lengkap: Clear cache & force stop -> Reset ID Iklan -> Airplane mode 3s -> Launch clone app."""
        print("\n" + "="*60)
        print(f" MEMULAI RESET ATOMIK CLONE: {CLONE_APPS.get(clone_key, {}).get('name', clone_key)}")
        print("="*60)
        if not self.force_stop_and_clear_cache(clone_key, stop_checker=stop_checker):
            return False
        if reset_ad_id:
            self.reset_advertising_id(stop_checker=stop_checker)
        if not self.toggle_airplane_mode(airplane_seconds, stop_checker=stop_checker):
            return False
        if not self.launch_clone_app(clone_key, stop_checker=stop_checker):
            return False
        print("="*60 + "\n")
        return True

    def push_qr_image(self, local_path: str, remote_filename: str = "qris_pay.png") -> Tuple[bool, str]:
        """
        Push gambar QR langsung ke folder Download (/sdcard/Download/):
        1. Bersihkan sisa gambar QR sebelumnya di Download.
        2. Push HANYA 1 file QR terbaru ke /sdcard/Download/{remote_filename}.
        3. Panggil Media Scanner agar terindeks seketika di galeri.
        """
        if not os.path.exists(local_path):
            print(f"[!] File QR lokal tidak ditemukan: {local_path}")
            return False, ""

        print("[*] Membersihkan cache gambar QR lama dari perangkat...")
        clean_cmd = (
            "rm -f /sdcard/Download/*qris* /sdcard/download/*qris* "
            "/sdcard/DCIM/Camera/*qris* /sdcard/Pictures/*qris*"
        )
        self.run(f'shell "{clean_cmd}"')

        # Pastikan direktori Download tersedia
        self.run('shell "mkdir -p /sdcard/Download"')

        # Push HANYA 1 file QR terbaru ke /sdcard/Download/
        remote_path = f"/sdcard/Download/{remote_filename}"
        print(f"[*] Mengirim gambar QR ke HP: {remote_path}...")
        self.run(f'push "{local_path}" "{remote_path}"')

        # Update timestamp terkini
        self.run(f'shell "touch {remote_path}"')

        # Panggil Media Scanner agar terindeks seketika di urutan paling atas galeri
        self.run(f'shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file://{remote_path}"')

        # Daftarkan ke Android MediaStore
        self.run(
            f'shell content insert --uri content://media/external/images/media '
            f'--bind _data:s:{remote_path} --bind mime_type:s:image/png'
        )
        time.sleep(0.5)

        print(f"[V] Gambar QR berhasil dikirim ke {remote_path}!")
        return True, remote_path

    def tap(self, x: int, y: int, delay_after: float = 1.0):
        """Mengetuk koordinat layar HP."""
        self.run(f"shell input tap {x} {y}")
        if delay_after > 0:
            time.sleep(delay_after)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, delay_after: float = 1.0):
        """Menggeser layar HP."""
        self.run(f"shell input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if delay_after > 0:
            time.sleep(delay_after)

    def keyevent(self, code: int, delay_after: float = 1.0):
        """Menekan tombol sistem (misal: 4=Back, 187=App Switcher, 3=Home)."""
        self.run(f"shell input keyevent {code}")
        if delay_after > 0:
            time.sleep(delay_after)

    def text_input(self, text: str, delay_after: float = 1.0):
        """Mengetik teks secara langsung melalui ADB."""
        escaped = str(text).replace(" ", "%s").replace("&", "\&")
        self.run(f"shell input text {escaped}")
        if delay_after > 0:
            time.sleep(delay_after)

    def type_pin(self, pin: str, keypad_coords: Optional[Dict[str, Dict[str, int]]] = None, delay_step: float = 0.25):
        """
        Mengetik PIN transaksi 6 digit menggunakan pemetaan koordinat keypad presisi.
        """
        coords = keypad_coords or DEFAULT_KEYPAD_COORDS
        print(f"[*] Mengetik PIN transaksi ({len(pin)} digit)...")
        for digit in str(pin):
            if digit in coords:
                x = coords[digit]["x"]
                y = coords[digit]["y"]
                self.tap(x, y, delay_after=delay_step)
            else:
                print(f"[!] Digit keypad '{digit}' tidak ditemukan dalam pemetaan.")
        time.sleep(1.0)
        print("[V] PIN transaksi selesai diketik.")

    def get_clipboard_text(self) -> str:
        """Membaca isi clipboard dari perangkat Android atau Windows host."""
        # 1. Coba baca dari sistem Android cmd clipboard
        try:
            out = self.run("shell cmd clipboard get")
            if out and not out.startswith("No shell") and not out.startswith("Error"):
                txt = out.strip()
                if txt.startswith("0x") and len(txt) == 42:
                    return txt
        except Exception:
            pass

        # 2. Coba baca dari Windows Host Clipboard (karena scrcpy menyinkronkan clipboard HP)
        try:
            p = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                capture_output=True,
                text=True,
                timeout=2
            )
            txt = p.stdout.strip()
            if txt.startswith("0x") and len(txt) == 42:
                return txt
        except Exception:
            pass

        return ""

    def read_required_usdc_from_screen(self) -> Optional[float]:
        """
        Membaca nominal USDC yang dibutuhkan dari layar 'Tinjau order' Bitget Wallet.
        Contoh teks pada node UI: 'Jumlah pembayaran\n1.0544 USDC'.
        """
        try:
            dump_remote = "/sdcard/temp_review_dump.xml"
            dump_local = os.path.join(CORE_DIR, ".temp_review_dump.xml")
            self.run(f"shell uiautomator dump {dump_remote}")
            self.run(f'pull {dump_remote} "{dump_local}"')
            self.run(f"shell rm -f {dump_remote}")

            if not os.path.exists(dump_local):
                return None

            import xml.etree.ElementTree as ET
            tree = ET.parse(dump_local)
            if os.path.exists(dump_local):
                os.remove(dump_local)

            for node in tree.getroot().iter("node"):
                desc = node.attrib.get("content-desc", "")
                text = node.attrib.get("text", "")
                combined = f"{text}\n{desc}".strip()
                if "Jumlah pembayaran" in combined:
                    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*USDC", combined)
                    if m:
                        return float(m.group(1))
        except Exception as e:
            print(f"[!] Gagal membaca nominal USDC dari layar: {e}")
        return None

    def extract_evm_address_from_screen(self) -> Optional[str]:
        """
        Mengekstrak alamat EVM Tuyul langsung dari layar 'Terima USDC'.
        Menghilangkan karakter invisible zero-width spaces (\u200b) yang disematkan UI Bitget.
        """
        try:
            dump_remote = "/sdcard/temp_addr_dump.xml"
            dump_local = os.path.join(CORE_DIR, ".temp_addr_dump.xml")
            self.run(f"shell uiautomator dump {dump_remote}")
            self.run(f'pull {dump_remote} "{dump_local}"')
            self.run(f"shell rm -f {dump_remote}")

            if not os.path.exists(dump_local):
                return None

            import xml.etree.ElementTree as ET
            tree = ET.parse(dump_local)
            if os.path.exists(dump_local):
                os.remove(dump_local)

            for node in tree.getroot().iter("node"):
                desc = node.attrib.get("content-desc", "")
                text = node.attrib.get("text", "")
                combined = f"{text} {desc}".replace("\u200b", "").strip()
                m = re.search(r"(0x[a-fA-F0-9]{40})", combined)
                if m:
                    return m.group(1)
        except Exception as e:
            print(f"[!] Gagal mengekstrak address EVM dari layar: {e}")
        return None
