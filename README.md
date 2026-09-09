# 🚀 BOT AUTO WD XLM BITGET WALLET (ADB MULTI-DEVICE)

Bot otomatisasi cerdas untuk melakukan **Withdraw (WD) XLM secara massal** dari banyak akun kloningan aplikasi Bitget Wallet di Android menggunakan ADB (*Android Debug Bridge*).

---

## ✨ Fitur Utama
- 🖥️ **CLI Interaktif:** Menu utama interaktif di terminal untuk kemudahan navigasi.
- 📐 **Auto-Set & Auto-Restore Layar:** Otomatis menyesuaikan resolusi & DPI layar HP ke standar bot (`1080x2400 @ 352 DPI`) saat berjalan, dan otomatis mengembalikan layar ke setelan bawaan pabrik setelah selesai / dihentikan.
- 📱 **Multi-Device Support:** Kompatibel dengan Poco F4, Poco X3, Poco X7/Pro, Poco F7/Pro, Poco X8/Pro, dan tipe HP Android lainnya.
- 🔢 **PIN Dinamis:** Tidak perlu utak-atik kordinat untuk ganti PIN. Cukup ganti PIN lewat menu, bot otomatis memetakan ketukan angka secara dinamis.
- 🔄 **Otomatisasi Alur Penuh (Step 0 - 42):**
  - Bypass pergantian clone di Multi App Ultra.
  - Penarikan saldo Max XLM.
  - Pengikatan 2FA Google Authenticator otomatis & input OTP *real-time*.
  - Pembersihan memori RAM (*Kill All Apps*) setelah tiap siklus akun.
- 💻 **Dukungan Dua Platform:** Bisa dijalankan via **PC/Laptop (Windows)** dengan *screen mirroring* (QtScrcpy), maupun langsung dari **HP via Termux** (*Wireless Debugging*).

---

## 🛠️ Persyaratan Sistem & Aplikasi

### 📱 Di HP Android:
1. **Multi App Ultra** *(Package: `com.waxmoon.ma.gp`)* - Untuk membuat kloningan Bitget.
2. **Bitget Wallet** *(Clone sudah dibuat di dalam Multi App)*.
3. **Google Authenticator** *(Untuk 2FA)*.
4. **Opsi Pengembang (Developer Options):**
   - *Debugging USB* / *USB Debugging* diaktifkan.
   - *Proses Debug Nirkabel* / *Wireless Debugging* diaktifkan (khusus mode WiFi / Termux).

### 💻 Di PC / Laptop (Windows):
- Python 3.8+ terinstall (Centang *"Add Python to PATH"* saat instalasi).
- File pendukung ADB dan QtScrcpy sudah tersedia di dalam folder `core/`.

### 📱 Di Android (Termux):
- Aplikasi **Termux** (Disarankan unduh dari F-Droid).

---

## 📥 PANDUAN PENGGUNAAN DI PC / WINDOWS

### 1. Jalankan Menu Utama
Buka folder project ini di PC Anda, lalu **Double-Click file `GAS WD.bat`**:

```bash
python core/menu.py
```

### 2. Koneksikan HP ke PC
Di Menu Utama, pilih menu **`6. KONEK ADB & SCRCPY (KHUSUS PC)`**:
- **Opsi 1 / 4 (Rekomendasi):** Sambungkan HP pakai kabel USB, jalankan Auto-Setup, lalu buka QtScrcpy untuk melihat layar HP secara langsung.

### 3. Jalankan Bot
- **Menu 1:** `MULAI WD (OTOMATIS FULL)` $\rightarrow$ Bot memproses seluruh akun tanpa henti.
- **Menu 2:** `MULAI WD MANUAL (STEP-BY-STEP)` $\rightarrow$ Bot berjalan langkah demi langkah (tekan ENTER untuk lanjut, cocok untuk uji coba/kalibrasi).

---

## 📥 PANDUAN PENGGUNAAN DI TERMUX (ANDROID TANPA PC)

Jalankan perintah berikut di aplikasi Termux Anda secara berurutan:

### 1. Update & Setup Otomatis (Cukup Copy-Paste Baris Ini):
```bash
pkg update -y && pkg upgrade -y && pkg install git -y && bash termux.sh
```

### 2. Buka Menu Utama:
```bash
bash termux.sh
```

### 3. Alur di Menu Termux:
1. Pilih **Opsi 6** (`KONEK ADB LOKAL`) $\rightarrow$ Masukkan IP & Port Wireless Debugging HP Anda.
2. Pilih **Opsi 1** (`MULAI WD OTOMATIS`) untuk langsung memulai proses penarikan saldo massal.

---

## ⚙️ KONFIGURASI (`core/config.json`)

Pengaturan dasar tersimpan di file `core/config.json` dan dapat diubah langsung lewat Menu Utama (**Opsi 3**):

```json
{
    "total_akun": 5,
    "start_index": 51,
    "alamat_wd": "ALAMAT_STELLAR_XLM_ANDA",
    "pin": "080808",
    "keypad_coords": {
        "1": { "x": 177, "y": 1898 },
        "2": { "x": 546, "y": 1898 },
        "3": { "x": 908, "y": 1898 },
        "4": { "x": 177, "y": 2014 },
        "5": { "x": 546, "y": 2014 },
        "6": { "x": 908, "y": 2014 },
        "7": { "x": 177, "y": 2130 },
        "8": { "x": 546, "y": 2130 },
        "9": { "x": 908, "y": 2130 },
        "0": { "x": 546, "y": 2258 }
    }
}
```

---

## 📱 CHEAT SHEET PERINTAH ADB LAYAR (MANUAL)

Jika Anda ingin mengatur atau memeriksa dimensi layar HP secara manual lewat CMD / Terminal / QtScrcpy:

### 🔍 Cek Info Layar & DPI Saat Ini:
```bash
adb shell "wm size && wm density"
```

### 🟢 Samakan Layar ke Format Acuan Bot (Poco F4 - 1080x2400 @ 352 DPI):
```bash
adb shell "wm size 1080x2400 && wm density 352"
```

### 🔄 Kembalikan Layar ke Bawaan Asli HP (Reset Total):
```bash
adb shell "wm size reset && wm density reset"
```

---

## 📐 DOKUMENTASI TEKNIS KOORDINAT
Untuk melihat tabel rincian seluruh 42 langkah klik, swipe, jeda waktu (*timing*), dan alur 2FA secara mendalam, silakan baca:
👉 **[core/KOORDINAT_DAN_ALUR.md](core/KOORDINAT_DAN_ALUR.md)**
