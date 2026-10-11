# 📘 DOKUMENTASI SPESIFIKASI & IMPLEMENTASI WEB POS: BOT BUAT AKUN BITGET WALLET (ACCOUNT CREATOR)

Dokumen ini berisi panduan teknis, arsitektur backend, spesifikasi API endpoint, alur kerja 26-step macro, serta panduan integrasi ke **Dashboard Web POS / Web3 Sweeper Auto-Wallet** (Sesuai antarmuka UI tombol `⚡ Buat Akun (Flow)`).

---

## 📄 1. Ringkasan Fitur & Tujuan Integrasi

Modul **Bitget Wallet Account Creator** dirancang untuk mengotomatisasi pembuatan dompet baru secara massal pada aplikasi Bitget Wallet di perangkat Android (via ADB) melalui antarmuka Web POS.

### 🌟 Fitur Utama:
1. **Smart Slot Selection**: Membuka clone aplikasi Bitget secara otomatis dari Multi App / Dual Space (Slot #1 s/d Slot #7 per halaman) sesuai nomor urut akun.
2. **Dynamic PIN Keypad Entry**: Menginput PIN transaksi 6-digit secara otomatis menggunakan pemetaan koordinat sentuh keypad layar HP yang presisi (`config.json`).
3. **Relay Referral Chaining**: 
   - Akun #1 di-bind menggunakan `master_referral_code` (misal: `JtzeyDtC`).
   - Setelah bind, bot menyalin kode referral milik Akun #1 dan menyimpannya ke `config.json` komputer.
   - Akun #2 otomatis menggunakan kode referral milik Akun #1, Akun #3 menggunakan kode Akun #2, dan seterusnya secara estafet (*relay chaining*).
   - **Proteksi Memory**: Kode referral disimpan di memori komputer (`config.json`) sehingga **tidak akan pernah tertimpa** oleh kode OTP email di clipboard HP.
4. **Auto Multi-IMAP OTP Fetcher**:
   - Membaca baris email ke-`N` dari file `core/emails.txt` (format `email|password_imap`).
   - Menghubungkan ke server IMAP SSL (Gmail, Outlook, Yahoo, Custom domain), mengekstrak 6-digit OTP verifikasi Bitget terbaru, dan mengetikkannya otomatis via perintah ADB (`shell input text OTP`).
5. **26-Step Granular Macro Control**: Seluruh langkah dapat di-toggle `ON` / `OFF` dan diedit jeda waktunya (`sleep`) secara langsung dari file `kordinat_create_account.txt` atau melalui Web UI.

---

## 🏗️ 2. Arsitektur Sistem & Komponen Files

```
SCRIPT ADB WD XLM BITGET/
├── core/
│   ├── create_account.py              # Script Engine Utama (ADB Executor, State Loop, Referral & IMAP Handler)
│   ├── kordinat_create_account.txt    # File Master 26-Step Macro Perintah ADB, Koordinat & Sleep Jeda
│   ├── imap_helper.py                 # Engine Pengambil OTP Email via Protokol IMAP SSL (Multi Email)
│   ├── emails.txt                     # Database Daftar Email KYC & Password Aplikasi/IMAP (Format email|pass)
│   ├── config.json                    # Konfigurasi JSON (PIN, Referral Relay, Slot Coords, Keypad Coords)
│   ├── created_accounts.json          # Database History Log Akun yang Sukses Dibuat
│   ├── server.py                      # Flask REST API & Web POS Server
│   └── web/                           # Frontend Asset Web POS Dashboard (HTML, CSS, JS)
```

---

## 🔌 3. Spesifikasi REST API Endpoint Backend (Flask `server.py`)

Untuk menghubungkan tombol `⚡ Buat Akun (Flow)` di Web POS, endpoint API berikut diimplementasikan di `core/server.py`:

### 3.1. Memulai Bot Buat Akun (`POST /api/create_account/start`)
* **Request Body**:
  ```json
  {
    "mode": "auto",                // Options: "auto", "manual", "rekam"
    "start_index": 1,              // Urutan akun/slot clone yang mulai dieksekusi
    "master_referral": "JtzeyDtC"  // (Opsional) Mengupdate kode referral induk awal
  }
  ```
* **Response (Success 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Bot Buat Akun Bitget berhasil dijalankan dalam mode auto.",
    "account_start": 1,
    "referral_active": "JtzeyDtC"
  }
  ```

### 3.2. Menghentikan Bot (`POST /api/create_account/stop`)
* **Request Body**: `{}`
* **Response (Success 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Bot Buat Akun berhasil dihentikan."
  }
  ```

### 3.3. Mengambil Status & Real-Time Log (`GET /api/create_account/status`)
* **Response (Success 200 OK)**:
  ```json
  {
    "bot_state": "RUNNING",        // "IDLE", "RUNNING", "WAITING_NEXT"
    "current_account": 2,
    "current_referral_code": "4mDtXXDj",
    "master_referral_code": "JtzeyDtC",
    "total_emails_available": 10,
    "last_updated": "2026-09-18 13:25:00"
  }
  ```

### 3.4. Membaca & Mengubah Step Macro (`GET & POST /api/create_account/steps`)
* **GET `/api/create_account/steps`**: Mengembalikan daftar 26 step beserta nama, koordinat, jeda `sleep`, dan status `ON/OFF`.
* **POST `/api/create_account/steps/toggle`**:
  * **Request Body**: `{"step_id": 19, "enabled": false}`
  * **Response**: `{ "status": "success", "step_id": 19, "enabled": false }`

---

## ⚡ 4. Tabel Rincian Alur Lengkap 26 Step Macro (`kordinat_create_account.txt`)

| Step ID | Nama Langkah / Aksi | Perintah ADB & Koordinat Piksel | Jeda Default | Deskripsi & Fungsi |
| :---: | --- | --- | :---: | --- |
| **Step 1** | Buka Clone Bitget via Slot | `input slot_tap {ACCOUNT_NUM}` | 3.0s | Mengetuk slot clone akun ke-`N` di Dual Space / Multi App |
| **Step 2** | Klik Buat Dompet Baru | `input tap 508 1967` | 2.0s | Mengetuk tombol "Buat Dompet" / "Create a Wallet" |
| **Step 2.1**| Pilih Create Seed Phrase Wallet | `input tap 542 2131` | 2.0s | Mengetuk opsi "Create seed phrase wallet" pada modal |
| **Step 3** | Input PIN Pertama | `pin {PIN} 1.0` | 1.0s | Menginput 6-digit PIN transaksi pertama (misal: 080808) |
| **Step 4** | Konfirmasi PIN Kedua | `pin {PIN} 2.0` | 2.0s | Menginput ulang 6-digit PIN transaksi kedua |
| **Step 5** | Lewati Biometric Fingerprint | `input tap 538 2186` | 5.0s | Mengetuk "Lewati / Nanti saja" pada dialog sidik jari |
| **Step 6** | Menu Pojok Kanan Atas | `input tap 995 129` | 2.0s | Mengetuk ikon menu / Orang+ di kanan atas beranda |
| **Step 7** | Step 1 Info Next | `input tap 542 2220` | 1.0s | Mengetuk Next 1 pada info referral |
| **Step 8** | Step 2 Info Next | `input tap 538 2213` | 1.0s | Mengetuk Next 2 pada info referral |
| **Step 9** | Earn Rebates Now | `input tap 555 2223` | 2.0s | Mengetuk tombol Earn Rebates Now |
| **Step 10**| Tombol Bind | `input tap 896 1207` | 2.0s | Mengetuk tombol Bind Kode Referral |
| **Step 11**| Tempel Kode Referral Relay | `input tap 307 2165` + `input text {REFERRAL_CODE}` | 1.0s | Menginput `{REFERRAL_CODE}` relay dari `config.json` |
| **Step 12**| Bind Konfirmasi | `input tap 746 2135` | 3.0s | Mengetuk tombol Konfirmasi Bind Referral |
| **Step 13**| Tutup Pop-up | `input tap 514 1044` | 2.0s | Mengetuk tombol tutup pop-up konfirmasi |
| **Step 14**| Salin Kode Referral Tuyul | `input tap 913 819` + `input copy_own_referral` | 1.0s | Mengetuk ikon copy & menyimpan kode baru ke `config.json` |
| **Step 15**| Tombol Back | `input keyevent 4` | 2.0s | Menekan tombol kembali Android ke beranda |
| **Step 16**| Ikon QR Scan | `input tap 865 126` | 2.0s | Mengetuk ikon scanner QR di pojok kanan atas |
| **Step 17**| Ikon Galeri | `input tap 1019 129` | 2.0s | Mengetuk ikon galeri pada scanner |
| **Step 18**| Pilih QR Barcode Galeri | `input tap 187 1146` | 1.0s | Memilih gambar QR barcode di galeri |
| **Step 19**| Tombol Done | `input tap 951 2230` | 3.0s | Mengetuk tombol Done / Selesai scan |
| **Step 20**| Get Started | `input tap 542 2060` | 2.0s | Mengetuk tombol Get Started |
| **Step 21**| Centang Persetujuan | `input tap 61 1654` | 1.0s | Mengetuk checkbox persetujuan syarat & ketentuan |
| **Step 22**| Continue with Email | `input tap 538 1894` | 2.0s | Mengetuk tombol Lanjut dengan Email |
| **Step 23**| Input Email KYC Tuyul | `input tap 514 571` + `input type_kyc_email` | 1.0s | Mengisi email dari `core/emails.txt` sesuai nomor akun |
| **Step 24**| Minta Kode OTP Email | `input tap 528 2203` | 5.0s | Mengetuk tombol Kirim Kode OTP Email |
| **Step 25**| Auto Fetch IMAP & Type OTP | `input tap 947 744` + `input imap_fetch_and_type_otp` | 2.0s | Membaca OTP dari server IMAP & mengetikkan via ADB |

---

## 🎨 5. Panduan Integrasi Frontend UI Web POS (`media_1789712875178.png`)

Berdasarkan rancangan visual antarmuka Web POS:

1. **Tombol `⚡ Buat Akun (Flow)`**:
   - Terhubung dengan handler event `onClick` JavaScript:
     ```javascript
     async function startCreateAccountFlow() {
         const masterRef = document.getElementById("referralInput").value.strip() || "JtzeyDtC";
         const res = await fetch("/api/create_account/start", {
             method: "POST",
             headers: { "Content-Type": "application/json" },
             body: JSON.stringify({
                 mode: "auto",
                 start_index: currentAccountIndex,
                 master_referral: masterRef
             })
         });
         const data = await res.json();
         if (data.status === "success") {
             showNotification("Bot Buat Akun Berhasil Dimulai!", "success");
         }
     }
     ```

2. **Form Referral Code Input (`4mDtXXDj`)**:
   - Kolom ini menampilkan kode referral yang sedang aktif diproduksi oleh tuyul aktif (`current_referral_code`).
   - Pengguna dapat mengetik ulang kode referral induk dan menekan tombol `📋 Ketik Referral` untuk memaksa update ke `config.json`.

3. **Status Banner USB ADB**:
   - Menampilkan status konektivitas perangkat Android yang terhubung (contoh: `USB ADB: b9f70fe7`).

---

## 🛡️ 6. Jaminan Keamanan Memory (Proteksi Referral vs OTP)

Antara pengetikan **Kode Referral** dan **Kode OTP Email**:
- **Tidak Menggunakan System Clipboard HP untuk Paste**: Pengetikan kode referral maupun OTP dilakukan murni via **ADB Direct Typing** (`adb shell input text VALUE`).
- **File Storage Terpisah**:
  - Kode Referral disimpan di: `core/config.json` (`current_referral_code`).
  - Email & IMAP Password disimpan di: `core/emails.txt`.
  - Log Akun Berhasil disimpan di: `core/created_accounts.json`.
- Dengan arsitektur ini, kode referral tidak akan pernah terhapus, tertimpa, atau korup saat proses fetching OTP berlangsung.

---

## 📝 7. Kesimpulan & Langkah Selanjutnya

Dokumentasi ini siap dijadikan referensi teknis untuk menghubungkan backend Python dengan Web POS Frontend UI.  
Setelah Anda selesai melakukan **Rekam Delay HP**, nilai `sleep` pada `core/kordinat_create_account.txt` akan terupdate secara otomatis dan siap dipakai untuk eksekusi penuh dari Web POS!
