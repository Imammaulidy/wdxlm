# 📐 DOKUMENTASI KOORDINAT, ALUR LANGKAH & PENGATURAN LAYAR

Dokumentasi ini memuat seluruh detail teknis langkah otomatisasi, titik koordinat sentuh, pemetaan keypad PIN dinamis, serta perintah ADB untuk penyesuaian resolusi layar multi-perangkat.

---

## 📋 1. Tabel Alur Lengkap Bot (Step 0 s/d 42)

> **Standar Kanvas:** Resolusi `1080 x 2400` @ `352 DPI` *(Otomatis disetel oleh bot saat mulai dan otomatis di-restore ke setelan pabrik saat selesai)*.

| Step | Nama Langkah / Aksi | Perintah & Koordinat | Jeda (Detik) | Fungsi & Keterangan |
|:---:|---|---|:---:|---|
| **#0** | Scroll Multi App Ultra | `swipe(546, 820, 546, 500, duration=1200)` | 1.0s | Menggeser layar ke atas agar clone akun berikutnya muncul |
| **#1** | Klik Clone Bitget | `tap(164, 423)` | 6.6s | Membuka aplikasi kloningan Bitget Wallet |
| **#2** | Klik Tab Dompet (Klik 2x) | `tap(908, 2258)` *(2x)* | 1.8s + 1.6s | Memastikan tab dompet aktif dan refresh tampilan |
| **#2.1**| Tutup Popup Promo/Modal | `swipe(560, 1630, 580, 2377, duration=300)` | 2.3s | Swipe ke bawah untuk menutup modal banner/promo jika muncul |
| **#3** | Klik Menu Hadiah | `tap(212, 816)` | 3.2s | Masuk ke menu Reward / Hadiah XLM |
| **#4** | Klik Koin XLM | `tap(536, 1316)` | 2.4s | Memilih aset XLM pada daftar hadiah |
| **#5** | Klik Tombol Penarikan | `tap(533, 2302)` | 1.9s | Menekan tombol Tarik / Withdraw |
| **#6** | Input Alamat Tujuan WD | `tap(525, 631)` $\rightarrow$ `input_text(ALAMAT_WD)` | 0.8s + 1.7s | Memilih kolom alamat dan mengisi address Stellar (XLM) |
| **#7** | Klik Tombol Semua (Max) | `tap(969, 888)` | 1.6s | Menarik seluruh saldo XLM yang tersedia |
| **#8** | Klik Area Kosong | `tap(518, 1452)` | 1.3s | Menutup keyboard virtual Android |
| **#9** | Klik Konfirmasi Penarikan | `tap(541, 2307)` | 1.2s | Membuka dialog konfirmasi transfer |
| **#10**| Klik Konfirmasi Lagi | `tap(800, 2156)` | 1.2s | Menyetujui modal peringatan transfer koin |
| **#11**| Klik Selanjutnya (Ikat OTP)| `tap(530, 2307)` | 2.4s | Masuk ke halaman integrasi 2FA Google Authenticator |
| **#12**| Klik Salin Kunci Setup | `tap(982, 1106)` | 1.0s | Menyalin (*copy*) Key 2FA rahasia ke clipboard |
| **#13**| Klik Selanjutnya | `tap(531, 1676)` | 1.2s | Melanjutkan ke halaman verifikasi OTP |
| **#14**| Buka Google Authenticator | *Intent: `com.google.android.apps.authenticator2`* | 2.5s | Membuka aplikasi Google Authenticator |
| **#15**| Klik Tambah Kode (+) | `tap(985, 2287)` | 1.4s | Menekan tombol plus bulat di kanan bawah |
| **#16**| Masukkan Kunci Penyiapan | `tap(963, 2066)` | 1.2s | Memilih opsi "Enter a setup key" |
| **#17**| Input Nama Akun | `tap(166, 320)` $\rightarrow$ `input_text(Nomor_Akun)` | 1.0s + 0.8s | Memberi label akun sesuai nomor urut clone |
| **#18**| Paste Kunci Setup | `tap(338, 508)` $\rightarrow$ `paste_clipboard()` | 1.0s + 1.1s | Menempelkan kunci 2FA yang telah disalin |
| **#19**| Tutup Keyboard | `press_back()` *(Keycode 4)* | 0.9s | Menekan tombol Back sistem |
| **#20**| Klik Tombol Tambahkan | `tap(536, 2279)` | 2.1s | Menyimpan akun baru di Google Auth |
| **#21**| Klik Tutup Layar Blank | `tap(983, 2256)` | 1.0s | Melewati dialog pengingat Google Auth |
| **#22**| Scroll Bawah List OTP | `swipe(525, 2140, 556, 220, duration=1000)` *(2x)* | 0.6s + 0.4s | Menggeser daftar OTP ke entri paling bawah |
| **#23**| Salin Kode OTP Terbawah | `tap(535, 2285)` | 1.0s | Menyentuh kode OTP paling baru untuk menyalin 6 digit |
| **#24**| Buka Recent Apps | `open_recent_apps()` *(Keycode 187)* | 0.9s | Membuka menu aplikasi terbaru Android |
| **#25**| Pilih Bitget Wallet | `tap(851, 1329)` | 1.1s | Kembali ke jendela aplikasi Bitget Wallet |
| **#26**| Klik Tombol Tempel (Paste)| `tap(920, 426)` | 0.6s | Menempel kode OTP 6-digit di Bitget |
| **#27**| Klik Tombol Ikat | `tap(525, 2310)` | 1.2s | Mengikat keamanan 2FA ke akun |
| **#28**| Beralih Opsi Keamanan | `tap(528, 1270)` | 1.1s | Menutup dialog fingerprint bawaan |
| **#29**| Pilih Beralih ke PIN | `tap(546, 2302)` | 0.9s | Memilih metode verifikasi via PIN transaksi |
| **#30**| Ketik 6 Digit PIN | `tap_dynamic_pin(PIN, KEYPAD)` | Dinamis | Menginput 6 digit PIN sesuai mapping `config.json` |
| **#31**| Klik Konfirmasi WD | `tap(536, 2302)` | 0.9s | Menekan konfirmasi final transaksi |
| **#32**| Paste OTP Final | `tap(946, 2027)` | 0.4s | Menempelkan OTP pada modal otentikasi penarikan |
| **#33**| Klik Tombol Otentikasi | `tap(797, 2233)` | 1.2s | Mengirim verifikasi otentikasi |
| **#34**| Beralih Opsi Keamanan | `tap(495, 1093)` | 1.0s | Menutup dialog fingerprint kedua |
| **#35**| Pilih Beralih ke PIN | `tap(531, 2302)` | 0.9s | Memilih verifikasi PIN akhir |
| **#36**| Ketik 6 Digit PIN Akhir | `tap_dynamic_pin(PIN, KEYPAD)` | Dinamis | Menginput PIN transaksi untuk melepas saldo XLM |
| **#37**| Klik Tombol Oke | `tap(533, 2310)` | 0.5s | Menutup dialog penarikan berhasil |
| **#38**| Buka Multi App Ultra | *Intent: `com.waxmoon.ma.gp`* | 1.0s | Kembali ke layar beranda Multi App |
| **#40**| Klik Titik Tiga | `tap(1032, 145)` | 0.6s | Membuka menu opsi Multi App |
| **#41**| Klik Kill All Apps | `tap(773, 273)` | 0.9s | Memilih opsi tutup semua aplikasi yang berjalan |
| **#42**| Klik Confirm Kill Apps | `tap(846, 1284)` | 5.5s | Mengonfirmasi penutupan clone agar memori RAM bersih |

---

## 🔢 2. Pemetaan Keypad PIN Dinamis (`config.json`)

Keypad diatur secara dinamis sehingga jika PIN Anda diubah di menu, bot secara otomatis menekan koordinat angka yang sesuai:

```json
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
```

---

## 📱 3. Kumpulan Perintah ADB Pengaturan Layar (Terminal Cheat Sheet)

Semua perintah di bawah ini siap Anda copy-paste langsung ke Terminal / CMD / QtScrcpy:

### 🔍 Cek Info Resolusi & DPI Saat Ini:
```bash
adb shell "wm size && wm density"
```

### 🟢 Samakan Layar ke Acuan Bot (Poco F4 - 1080x2400 @ 352 DPI):
```bash
adb shell "wm size 1080x2400 && wm density 352"
```

### 🔄 Kembalikan Layar ke Bawaan Asli HP (Restore Default):
```bash
adb shell "wm size reset && wm density reset"
```
