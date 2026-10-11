# 🚀 BOT AUTO WD XLM, CREATOR BITGET & QRIS MULTI-CHAIN EVM (ADB STANDALONE)

Ekosistem otomasi cerdas berkinerja tinggi untuk **Withdraw (WD) XLM Massal**, **Pembuatan Akun Dompet Bitget Baru (Create Account via IMAP OTP)**, dan **Bot QRIS Payment & Multi-Chain EVM (Base / Morph / Arbitrum / Polygon / BSC)** dari Bitget Wallet menggunakan ADB Android.

Mendukung eksekusi via **Web Dashboard (Port 2000)** dengan **PM2 24/7 Anti-Sleep (Away Mode)**, **Terminal All-in-One CLI**, serta **Termux Android Standalone** (ADB Wireless & Shizuku Non-Root).

---

## ⚡ SHORTCUT EKSEKUSI & CARA MENJALANKAN

### 🌐 1. Mode Web UI Dashboard (Port 2000 + PM2 24/7):
Double-click file batch di root folder:
```cmd
GAS WEB DASHBOARD.bat
```
* **Akses Otomatis LAN:** `http://<IP_LAN_KOMPUTER>:2000` (Contoh: `http://192.168.1.13:2000`)
* **Domain Publik Cloudflare:** `https://topnodtools.web.id`
* **Fitur PM2 Background & Anti-Sleep:**
  * Server berjalan di latar belakang via **PM2** (`bitget-server`).
  * Mengaktifkan **Away Mode** Windows (`SetThreadExecutionState` + `powercfg`) sehingga server dan bot tetap aktif bekerja meskipun layar laptop mati atau laptop ditutup (*lid closed*).
  * Dilengkapi menu interaktif: *Start Server, Status PM2, Stop Server, Restart Service, & Buka Browser*.

### 💎 2. Mode Bot QRIS & Multi-Chain EVM:
Double-click:
```cmd
GAS QRIS MORPH.bat
```
Atau via terminal:
```bash
python core/qris_morph.py
```

### 💻 3. Mode Terminal All-in-One (WD XLM & Creator):
Double-click:
```cmd
GAS WD.bat
```
Atau via terminal:
```bash
python core/menu.py
```

### 📱 4. Mode Termux (Android tanpa PC):
Jalankan runner interaktif di Termux:
```bash
bash run.sh
```
Runner Termux menyediakan menu 1-klik untuk:
1. Menjalankan Menu CLI Bot (`core/menu.py`)
2. Menjalankan WD XLM Mode Baru / Mode Old
3. Menjalankan Bot QRIS Cashback Multi-Chain
4. Menjalankan Web Dashboard Server di Port 2000
5. Auto-Connect ADB Wireless (`termux/konek_adb.py`)
6. Setup 1-Klik Shizuku (`rish`) Non-Root / Offline Data

### 🛑 5. Reset & Emergency ADB:
Jika koneksi ADB hang atau port bentrok:
```cmd
KILL_ADB.bat
```

---

## 📂 ARSITEKTUR STRUKTUR DIREKTORI (LEAN & CLEAN)

Struktur proyek telah dikelompokkan secara murni sesuai standar modular bebas dari *dead code*:

```text
SCRIPT ADB WD XLM BITGET/
├── GAS WEB DASHBOARD.bat       # Launcher Web UI, Tunnel & PM2 Controller
├── GAS WD.bat                  # Launcher Terminal All-in-One WD XLM
├── GAS QRIS MORPH.bat          # Launcher Terminal Bot QRIS Multi-Chain
├── KILL_ADB.bat                # Tool pembersih & reset proses ADB
├── run.sh                      # Launcher serbaguna untuk Termux Android
├── README.md                   # Dokumentasi resmi sistem
│
├── core/                       # ENGINE INTI SISTEM
│   ├── server.py               # Flask RESTful API & WebSocket Web Dashboard
│   ├── menu.py                 # Menu Controller All-in-One CLI
│   ├── wd_xlm.py               # Engine Automasi WD XLM (Mode Baru & Old)
│   ├── qris_morph.py           # Engine Automasi QRIS & Multi-Chain EVM
│   ├── create_account.py       # Engine Pembuatan Akun Baru Bitget
│   ├── gobiz_qris.py           # Engine Generator & Transaksi QRIS GoBiz
│   ├── evm_wallet.py           # Multi-Chain EVM On-Chain Transfer Engine
│   ├── imap_helper.py          # Pembaca OTP Email Gmail via IMAP SSL
│   ├── adb_controller.py       # Driver ADB Wrapper & Clone App Management
│   ├── screen_manager.py       # Screen Protection & DPI Auto-Scaler
│   ├── wallet_phrase_helper.py # Pengelola Frasa & Mnemonic Dompet
│   ├── scrcpy_launcher.py      # Pengendali Mirror Screen Scrcpy
│   ├── create_autostart.py     # Script pendaftaran Autostart Windows
│   ├── AUTOSTART_WINDOWS.vbs   # Runner VBScript background Windows
│   ├── ecosystem.config.js     # Konfigurasi PM2 Process Manager
│   ├── config.json             # Konfigurasi aktif (Private)
│   ├── config.example.json     # Template konfigurasi bersih
│   ├── emails.txt              # Daftar email akun (Private)
│   │
│   ├── kordinat/               # FOLDER PENGELOMPOKAN KOORDINAT MACRO
│   │   ├── kordinat_wd_baru.txt        # Koordinat WD XLM Mode Baru
│   │   ├── kordinat_wd_old.txt         # Koordinat WD XLM Mode Old
│   │   ├── kordinat_create_account.txt # Koordinat Pembuatan Akun
│   │   └── kordinat_qris_morph.txt     # Koordinat QRIS Cashback
│   │
│   ├── web/                    # FRONTEND WEB DASHBOARD
│   │   ├── index.html          # UI Dashboard Single-Page
│   │   ├── css/                # Styling antarmuka
│   │   └── js/                 # Logika JavaScript real-time
│   │
│   ├── bin/                    # Binary runtime (cloudflared, tools)
│   └── scrcpy-win64-v3.3.4/    # Paket driver Scrcpy & ADB Windows
│
├── docs/                       # DOKUMENTASI TEKNIS & SPESIFIKASI
│   ├── IMPLEMENTASI_BOT_BUAT_AKUN_WEB_POS.md
│   ├── KOORDINAT_DAN_ALUR.md
│   └── KOORDINAT_DAN_ALUR_CREATE_ACCOUNT.md
│
├── termux/                     # MODUL OTOMASI ANDROID TERMUX
│   ├── konek_adb.py            # Auto-Connect & Scanner ADB Wireless
│   └── setup_shizuku.sh        # Installer 1-Klik Shizuku (rish) Non-Root
│
└── DATA WALLET BITGET/         # Folder Penyimpanan Frasa Dompet (Ignored)
```

---

## ✨ FITUR UTAMA & KEUNGGULAN SISTEM

### 1. 24/7 PM2 Background Service & Windows Anti-Sleep (Away Mode)
* Web server dan bot dapat berjalan stabil tanpa jeda di latar belakang menggunakan **PM2**.
* Menggunakan integrasi Windows API `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)` sehingga sistem operasi tidak masuk ke mode sleep/suspend saat layar mati.

### 2. Dual Mode NMID QRIS GoBiz (Standar EMVCo Presisi)
* **Mode Revisi (`revisi`) [Default / Paling Aman]:**
  * Mempertahankan **10 karakter awal NMID asli** (`clean_orig[:10]`, contoh: `ID10265931`).
  * Hanya mengacak **5 digit terakhir** (`k=5`). Menjamin 100% routing perbankan e-wallet sampai ke merchant asli tanpa kegagalan bayar.
* **Mode Bot Referensi (`referensi`):**
  * Format acak bawaan: `ID2026` + **9 digit angka acak** (total 15 karakter).
* **Nominal Presisi (`current + 1`):**
  * Tagihan QRIS dinamis dihitung secara murni bertambah 1 per transaksi tanpa nominal melompat ke generator acak.

### 3. Multi-Chain EVM Universal Wallet Dispenser
* **Dukungan Multi-Jaringan:**
  * Base Network (Coinbase L2) — Default (Chain ID: `8453`)
  * Morph L2 (Chain ID: `2818`)
  * Arbitrum One (Chain ID: `42161`)
  * Polygon PoS (Chain ID: `137`)
  * BNB Smart Chain (Chain ID: `56`)
* Pengecekan saldo gas native & saldo token ERC-20 (USDC) secara real-time sebelum melakukan injeksi dana ke wallet tuyul.

### 4. Zero-Factory-Reset Screen Protection
* Merekam resolusi fisik & DPI asli perangkat Android sebelum pengubahan format bot (`1080x2400 @ 352 DPI`).
* Mengembalikan resolusi asli perangkat secara otomatis saat bot dihentikan atau tombol Exit ditekan tanpa resiko merusak tampilan layar bawaan HP.

### 5. Multi-Device Detection & Port Binding Murni
* Mendukung deteksi multi-perangkat ADB secara bersamaan (USB & Wireless TCP).
* Server Flask mengunci binding langsung ke alamat IP LAN lokal (`http://<IP_LAN>:2000`) dan terintegrasi dengan domain Cloudflare Tunnel publik (`https://topnodtools.web.id`).

---

## ⚙️ CARA KONFIGURASI (`core/config.json`)

Contoh file template tersedia pada [`core/config.example.json`](core/config.example.json):

```json
{
    "active_chain": "base",
    "gobiz_active_index": 0,
    "gobiz_shift_rotation": true,
    "nmid_mode": "revisi",
    "pin": "080808",
    "referral_code": "4mDtXXDj",
    "start_index": 1,
    "total_akun": 10,
    "step2_mode": "dompet",
    "wallet_tebar": {
        "address": "0xYourWalletAddress...",
        "private_key": "0xYourPrivateKey..."
    }
}
```

* **`nmid_mode`**: Pilihan pengacakan NMID QRIS (`"revisi"` untuk mode presisi 10 karakter asli + 5 digit acak, atau `"referensi"` untuk ID2026 + 9 digit).
* **`step2_mode`**: Mode navigasi dompet di Bitget (`"dompet"` atau `"profil"`).
* **`wallet_tebar`**: Alamat dompet EVM dan Private Key pengirim saldo token.

---

## 📱 PANDUAN PENGGUNAAN DI TERMUX (ANDROID)

1. Buka Termux, clone/pindahkan folder proyek ke penyimpanan Termux:
   ```bash
   cd ~/SCRIPT\ ADB\ WD\ XLM\ BITGET
   ```
2. Jalankan runner utama:
   ```bash
   bash run.sh
   ```
3. Jika menggunakan koneksi **Shizuku (Tanpa Wi-Fi / Hotspot)**:
   * Pilih menu **[7] Setup 1-Klik Shizuku (rish)**.
   * Skrip akan otomatis mengekstrak `rish` & native library `librish.so` langsung dari APK Shizuku yang terpasang di HP dengan proteksi Android 14+ Read-Only DEX.
   * Klik **Always allow** saat notifikasi pop-up Shizuku muncul di layar HP.
4. Jika menggunakan **ADB Wireless**:
   * Pilih menu **[6] Auto-Connect ADB Wireless**.

---

## 🔒 KEAMANAN & PRIVASI DATA

* Direktori [`DATA WALLET BITGET/`](DATA%20WALLET%20BITGET/), file `config.json`, token kredensial, dan daftar email telah dimasukkan ke dalam [`.gitignore`](.gitignore).
* Jangan pernah mempublikasikan file konfigurasi asli atau private key ke repositori publik.
