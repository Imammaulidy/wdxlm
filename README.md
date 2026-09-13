# 🚀 BOT AUTO WD XLM BITGET WALLET (ADB MULTI-DEVICE)

Bot otomatisasi cerdas untuk melakukan **Withdraw (WD) XLM secara massal** dari akun kloningan Bitget Wallet menggunakan ADB, dilengkapi **Web UI Dashboard** modern berbasis Glassmorphism serta CLI terminal interaktif.

---

## ⚡ SHORTCUT MENJALANKAN BOT

### 🌐 Mode Web UI Dashboard (Rekomendasi PC):
Cukup double-click **`WEB_UI.bat`** di Windows!
Browser otomatis terbuka di:
👉 **`http://127.0.0.1:5000`**

### 💻 Mode Terminal / CLI (Windows):
Double-click **`GAS WD.bat`** atau jalankan via terminal:
```bash
python core/menu.py
```

### 📱 Mode Termux (Android tanpa PC):
Jalankan runner all-in-one di aplikasi Termux:
```bash
bash run.sh
```

---

## ✨ Fitur Utama

- 🌐 **Web UI Controller Dashboard:**
  - Dashboard modern bertema Dark Glassmorphism.
  - Streaming log terminal real-time via Server-Sent Events (SSE).
  - Kontrol one-click: Mulai Bot, Lanjut Loop Akun Berikutnya (ENTER), Stop Bot.
  - Shortcut keyboard: Cukup tekan tombol `ENTER` untuk melanjutkan ke clone berikutnya.
  - Pengelola visual 43 langkah macro (`kordinat.txt`): toggle switch ON/OFF dan edit jeda waktu (`sleep`).
  - Quick tools: Buka SCRCPY mirroring (120 FPS), set format bot, dan restore layar HP asli.
- 📐 **Zero-Factory-Reset Screen Protection:**
  - Otomatis membaca & merekam resolusi & DPI aktif yang sedang dipakai HP saat awal bot dijalankan.
  - Menerapkan format bot (`1080x2400 @ 352 DPI`).
  - Saat bot selesai atau ditutup, layar otomatis dipulihkan ke ukuran terekam (tanpa perintah `wm size reset` / `wm density reset`).
- 🔁 **Continuous Loop Account WD:**
  - Menyimpan nomor urutan clone terakhir (`start_index`) secara otomatis.
  - Selesai satu akun, bot berhenti sejenak dan menunggu konfirmasi ENTER sebelum mengeksekusi akun berikutnya.
- 📱 **Smart SCRCPY & Wi-Fi Auto-Detect:**
  - Deteksi otomatis koneksi USB dan IP Wi-Fi lokal (`wlan0`/`wlan1`).
  - Kabel USB dapat dicabut setelah tersambung tanpa mematikan sesi mirroring.
- 📝 **Script Koordinat Dinamis (`core/kordinat.txt`):**
  - Seluruh alur step, tap, swipe, sleep, dan PIN keypad 0–9 dapat dikustomisasi langsung.

---

## 🛠️ Persyaratan Sistem

### 📱 Di HP Android:
1. **Multi App Ultra** (`com.waxmoon.ma.gp`) — Aplikasi clone Bitget Wallet.
2. **Google Authenticator** — Aplikasi 2FA OTP.
3. **Opsi Pengembang (Developer Options):**
   - Aktifkan *Debugging USB* (untuk PC).
   - Aktifkan *Proses Debug Nirkabel* / *Wireless Debugging* (untuk Termux).

### 💻 Di PC / Windows:
- Python 3.8+ terinstall (dengan Flask: `pip install flask`).
- Driver ADB & scrcpy sudah tersedia di folder `core/`.

### 📱 Di Android (Termux):
- Unduh dan buka aplikasi **Termux** (disarankan versi F-Droid).

---

## 📥 PANDUAN PENGGUNAAN

### 🌐 1. Menggunakan Web UI Dashboard:
1. Hubungkan HP via kabel USB (USB Debugging aktif).
2. Jalankan file **`WEB_UI.bat`**.
3. Browser akan otomatis membuka `http://127.0.0.1:5000`.
4. Anda dapat:
   - Mengatur nomor clone awal, alamat wallet XLM, dan PIN.
   - Mengaktifkan/menonaktifkan langkah macro sesuai kebutuhan.
   - Mengklik tombol **Mulai Auto WD**.
   - Ketika selesai memproses 1 akun, tekan **Lanjut Clone Berikutnya** atau tekan tombol **ENTER** di keyboard.

### 💻 2. Menggunakan Menu Terminal (GAS WD.bat):
1. Jalankan **`GAS WD.bat`**.
2. Pilih **Opsi 7** (`KONEK ADB & SCRCPY`) untuk menghubungkan perangkat.
3. Pilih **Opsi 1** (`MULAI WD OTOMATIS FULL`) untuk memulai proses loop.

---

## ⚙️ PENGATURAN & SCRIPT KOORDINAT

### 📝 Edit Langkah & Koordinat (`core/kordinat.txt`)
Untuk melihat, menambah, merevisi seluruh koordinat klik, swipe, jeda waktu (*timing*), atau menonaktifkan step (tambah kata `OFF`), silakan buka:
👉 **[`core/kordinat.txt`](core/kordinat.txt)**

### 🔧 Konfigurasi (`core/config.json`)
Dapat diedit langsung lewat Web Dashboard, menu terminal (**Opsi 3**), atau manual:
```json
{
    "total_akun": 1,
    "start_index": 43,
    "alamat_wd": "0x41739ee3a2641B096D0F0DD2427796f2A55d85aa",
    "pin": "080808",
    "last_wifi_ip": "192.168.1.24",
    "disabled_steps": [0, 1, 11, 28, 29, 30, 33, 41, 42]
}
```
