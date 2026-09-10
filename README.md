# 🚀 BOT AUTO WD XLM BITGET WALLET (ADB MULTI-DEVICE)

Bot otomatisasi cerdas untuk melakukan **Withdraw (WD) XLM secara massal** dari akun kloningan Bitget Wallet menggunakan ADB.

---

## ⚡ SHORTCUT MENJALANKAN BOT

### 📱 Mode Termux (Android tanpa PC):
Cukup jalankan satu baris perintah all-in-one ini (otomatis install dependensi & buka menu):
```bash
bash run.sh
```

### 💻 Mode PC / Windows:
Cukup double-click **`GAS WD.bat`** atau jalankan via terminal:
```bash
python core/menu.py
```

---

## ✨ Fitur Utama
- 🖥️ **CLI Interaktif:** Menu navigasi lengkap di terminal (PC & Termux).
- 📐 **Auto-Set & Auto-Restore Layar:** Otomatis merekam resolusi & DPI asli HP, menyesuaikan ke standar bot (`1080x2400 @ 352 DPI`) saat mulai, dan otomatis mengembalikan ke ukuran terekam setelah selesai.
- 📝 **Script Koordinat Dinamis (`core/kordinat.txt`):** Seluruh perintah sentuh, swipe, jeda waktu (`sleep`), dan teks dibaca langsung dari file teks ala TopNod.
- 🎛️ **Fitur ON/OFF Step Dua Arah:** Langkah bot bisa diaktifkan/dinonaktifkan baik lewat Menu 4 di terminal maupun dengan menambahkan kata `OFF` pada judul step di `core/kordinat.txt`.
- 🔢 **PIN Keypad Dinamis:** Koordinat angka PIN 0–9 otomatis disesuaikan secara dinamis.
- 💻 **Dua Platform:** Mendukung Windows PC (dengan scrcpy mirroring) dan Android Termux (Wireless Debugging).

---

## 🛠️ Persyaratan Sistem

### 📱 Di HP Android:
1. **Multi App Ultra** (`com.waxmoon.ma.gp`) — Aplikasi clone Bitget Wallet.
2. **Google Authenticator** — Aplikasi 2FA OTP.
3. **Opsi Pengembang (Developer Options):**
   - Aktifkan *Debugging USB* (untuk PC).
   - Aktifkan *Proses Debug Nirkabel* / *Wireless Debugging* (untuk Termux).

### 💻 Di PC / Windows:
- Python 3.8+ terinstall (Centang *"Add Python to PATH"*).
- Driver ADB & scrcpy sudah tersedia di folder `core/`.

### 📱 Di Android (Termux):
- Unduh dan buka aplikasi **Termux** (disarankan versi F-Droid).

---

## 📥 PANDUAN PENGGUNAAN LENGKAP

### 📱 Menjalankan di Termux (Tanpa PC):
1. **Jalankan Runner All-in-One:**
   ```bash
   bash run.sh
   ```
   *(Script otomatis meminta izin storage, menginstal Python, NMAP, ADB, menyiapkan config, dan membuka menu utama).*
2. **Di Menu Utama:**
   - Pilih **Opsi 7** (`KONEK ADB LOKAL`) $\rightarrow$ Masukkan IP & Port Wireless Debugging.
   - Pilih **Opsi 1** (`MULAI WD OTOMATIS`) atau **Opsi 2** (`MULAI WD MANUAL`).

---

### 💻 Menjalankan di PC / Windows:
1. **Jalankan Menu:**
   Double-click file **`GAS WD.bat`** atau jalankan:
   ```bash
   python core/menu.py
   ```
2. **Hubungkan HP:**
   - Pilih **Opsi 7** (`KONEK ADB & SCRCPY`) $\rightarrow$ Pilih Opsi 1 (Cek device) atau Opsi 4 (Auto-Setup Wireless).
3. **Jalankan Bot:**
   - **Menu 1:** `MULAI WD (OTOMATIS FULL)`
   - **Menu 2:** `MULAI WD MANUAL (VIA ENTER / STEP-BY-STEP)`

---

## ⚙️ PENGATURAN & SCRIPT KOORDINAT

### 📝 Edit Langkah & Koordinat (`core/kordinat.txt`)
Untuk melihat, menambah, merevisi seluruh koordinat klik, swipe, jeda waktu (*timing*), atau menonaktifkan step (tambah kata `OFF`), silakan buka:
👉 **[`core/kordinat.txt`](core/kordinat.txt)**

### 🔧 Konfigurasi (`core/config.json`)
Dapat diedit langsung lewat menu terminal (**Opsi 3**) atau manual:
```json
{
    "total_akun": 1,
    "start_index": 0,
    "alamat_wd": "ALAMAT_EVM_ATAU_XLM_ANDA",
    "pin": "080808",
    "disabled_steps": [11, 25, 28, 29, 30, 33, 41, 42]
}
```

---

## 📱 PERINTAH MANUAL ADB LAYAR

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
