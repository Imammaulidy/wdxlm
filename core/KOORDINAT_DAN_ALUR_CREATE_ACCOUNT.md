# 📐 DOKUMENTASI KOORDINAT, REFERRAL CHAINING & IMAP OTP BITGET WALLET

Dokumentasi teknis alur pembuatan akun dompet baru (Create Account), **Referral Relay Chaining**, serta **Otomatisasi Verifikasi KYC Email IMAP OTP**.

> 💡 **FILE KOORDINAT AKTIF & PENANDA OFF:**  
> Seluruh koordinat, perintah sentuh, jeda waktu (`sleep`), dan teks dibaca langsung oleh bot dari file [`core/kordinat_create_account.txt`](kordinat_create_account.txt).  
> - **Cara Menonaktifkan Step:** Tambahkan kata `OFF` pada judul step di `kordinat_create_account.txt` (contoh: `[19. Referral Step 13 - Konfirmasi OTP & KYC] OFF`).  
> - **Sinkronisasi Dua Arah:** Status ON/OFF tersinkronisasi otomatis dengan `disabled_steps_create_account` di `config.json`.

---

## 🔗 1. Alur Referral Relay Chaining

1. **Akun #1 (Tuyul 1)**: Membaca `current_referral_code` (awalnya diisi `master_referral_code` misal `JtzeyDtC`).
2. **Bind & Copy**: Setelah bind referral, bot mengeksekusi `input copy_own_referral` untuk menyalin kode referral milik Akun #1 dari Bitget Wallet.
3. **Relay ke Akun #2**: Bot memperbarui `current_referral_code` di `config.json` dengan kode Akun #1, sehingga Akun #2 otomatis menggunakan kode dari Akun #1, Akun #3 memakai kode Akun #2, dan seterusnya secara berantai.

---

## 📧 2. Alur KYC Email & Auto IMAP OTP Fetcher

1. **Email Pool (`core/emails.txt`)**: Bot membaca baris email ke-`ACCOUNT_NUM` dari `emails.txt` (format `email@domain.com|password_imap`).
2. **Input Email (`input type_kyc_email`)**: Bot menginput email ke form KYC/Bind Email Bitget Wallet.
3. **Kirim OTP**: Bot menekan tombol Kirim Kode.
4. **Auto IMAP OTP (`input imap_fetch_and_type_otp`)**: Modul `imap_helper.py` terhubung ke server IMAP, membaca email verifikasi Bitget terbaru, mengekstrak 6-digit OTP, dan menginputnya otomatis via ADB.

---

## 📋 3. Tabel Alur Lengkap Bot (Step 1 s/d Step 22)

| Step | Nama Langkah / Aksi | Perintah & Koordinat | Jeda | Keterangan |
|:---:|---|---|:---:|---|
| **#1** | Buka Clone Bitget via Slot | `input slot_tap {ACCOUNT_NUM}` | 7.0s | Menekan slot clone sesuai nomor akun |
| **#2** | Klik Buat Dompet Baru | `tap(540, 1850)` | 2.5s | Menekan tombol "Buat Dompet" / "Create a wallet" |
| **#2.1**| Pilih Create Seed Phrase Wallet | `tap(540, 2040)` | 2.0s | Menekan opsi "Create seed phrase wallet" pada modal |
| **#3** | Input PIN Pertama | `pin {PIN} 1.5` | 1.5s | Menginput 6 digit PIN pertama |
| **#4** | Konfirmasi PIN Kedua | `pin {PIN} 2.5` | 2.5s | Konfirmasi 6 digit PIN kedua |
| **#5** | Lewati Biometric | `tap(540, 2300)` | 2.0s | Lewati dialog sidik jari |
| **#6** | Tunggu Inisialisasi | `sleep 5.0` | 5.0s | Menunggu inisialisasi dompet |
| **#7** | Referral Step 1 | `tap_rel 0.611987 0.820113` | 1.5s | Menekan Ikon Orang+ (Invite) di beranda |
| **#8** | Referral Step 2 | `tap_rel 0.536278 0.878187` | 1.2s | Menekan Info Next 1 |
| **#9** | Referral Step 3 | `tap_rel 0.533123 0.898017` | 1.2s | Menekan Info Next 2 |
| **#10**| Referral Step 4 | `tap_rel 0.552050 0.832861` | 1.2s | Menekan Info Get / Start |
| **#11**| Referral Step 5 | `tap_rel 0.523659 0.912181` | 1.2s | Menekan Form Input Kode Referral |
| **#12**| Referral Step 6 | `tap_rel 0.539432 0.848442` + `input text {REFERRAL_CODE}` | 1.2s | Tempel / Input Kode Referral Relay |
| **#13**| Referral Step 7 | `tap_rel 0.536278 0.919263` | 1.5s | Menekan Konfirmasi Bind Referral |
| **#14**| Referral Step 8 | `tap_rel 0.552050 0.848442` + `input copy_own_referral` | 1.5s | Salin Kode Referral Tuyul & update config |
| **#15**| Referral Step 9 | `tap_rel 0.536278 0.903683` | 1.5s | Lanjut ke Pengaturan Profil / KYC Email |
| **#16**| Referral Step 10 | `tap_rel 0.545741 0.842776` + `input type_kyc_email` | 1.2s | Input Email KYC dari `core/emails.txt` |
| **#17**| Referral Step 11 | `tap_rel 0.517350 0.896601` | 2.0s | Menekan Kirim Kode OTP Email |
| **#18**| Referral Step 12 | `tap_rel 0.517350 0.838527` + `input imap_fetch_and_type_otp` | 1.5s | Ambil OTP dari IMAP & ketik otomatis |
| **#19**| Referral Step 13 [OFF] | `tap_rel 0.536278 0.905099` | 1.5s | Konfirmasi OTP & Verifikasi |
| **#20**| Referral Step 14 [OFF] | `tap_rel 0.529968 0.839943` | 1.5s | Lewati Backup / Selesai |
| **#21**| Referral Step 15 [OFF] | `tap_rel 0.567823 0.913598` | 2.0s | Kembali ke Beranda / Multi App |
| **#22**| Kembali ke Multi App [OFF]| `input keyevent 187` | 1.5s | Membuka Recent Apps |
