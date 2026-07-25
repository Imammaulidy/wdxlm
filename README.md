# Auto WD XLM Bitget Wallet
Bot otomatisasi untuk melakukan Withdraw (WD) XLM secara massal dari banyak akun kloningan Bitget Wallet menggunakan ADB (Android Debug Bridge).

## 🚀 Fitur Utama
- **Interaktif CLI:** Memiliki Menu Utama interaktif bergaya terminal.
- **PIN Dinamis:** Tidak perlu hardcode kordinat layar lagi. Ubah PIN sesuka hati lewat menu, dan bot akan menghitung ketukan layar berdasarkan koordinat dinamis.
- **Support PC & Termux:** Dapat dijalankan dari laptop/PC (Windows) menggunakan kabel USB/Wi-Fi dengan bantuan layar *mirroring* (QtScrcpy), maupun mode nirkabel murni langsung dari HP via Termux.
- **Otomatisasi Penuh:**
  - Berpindah antar clone akun di aplikasi Multi App secara instan (*Bypass Package Invocation*).
  - WD XLM Max Amount secara otomatis.
  - Mengambil OTP dari aplikasi Google Authenticator.
  - Mengatur input PIN secara dinamis.
  - Bypass koneksi ADB dengan trik "Colok USB 5 Detik" untuk PC.

## 🛠️ Persyaratan
- **Aplikasi Pendukung di HP Android:**
  - Multi App Ultra (Untuk clone Bitget) - *Package: com.waxmoon.ma.gp*
  - Bitget Wallet
  - Google Authenticator
- **Untuk PC (Windows):** Terinstal Python 3. (Semua *tools* ADB dan QtScrcpy sudah disediakan di dalam paket/folder `templates`).
- **Untuk Termux (Android):** Aplikasi Termux dari F-Droid.

---

## 📥 Instalasi & Penggunaan di Termux (Android Tanpa PC)
Buka aplikasi Termux Anda, lalu jalankan perintah di bawah ini secara berurutan:

1. **Update sistem dan install Git:**
   ```bash
   pkg update -y && pkg upgrade -y
   pkg install git -y
   ```
2. **Clone repositori ini:**
   ```bash
   git clone https://github.com/imammaulidy/wdxlm.git
   cd wdxlm
   ```
3. **Jalankan Installer & Buka Menu Utama:**
   ```bash
   bash MENU_TERMUX.sh
   ```
4. **Cara Penggunaan di Termux:**
   - Di dalam `MENU_TERMUX.sh`, pilih **Opsi 1** untuk menginstal modul pertama kali.
   - Pilih **Opsi 2** untuk mengkoneksikan ADB Nirkabel secara otomatis.
   - Pilih **Opsi 3** untuk menjalankan Bot WD Massal.

---

## 📥 Instalasi & Penggunaan di Windows (PC/Laptop)
1. Buka CMD/Terminal di PC Anda.
2. Clone repositori ini:
   ```bash
   git clone https://github.com/imammaulidy/wdxlm.git
   ```
3. Masuk ke folder hasil clone, dan **Double-Click** file `MENU_UTAMA.bat`.
4. Anda akan disambut oleh Menu Interaktif. Silakan pilih menu untuk mengatur PIN, mengubah koordinat, menyambungkan HP (via Kabel/WiFi), hingga menjalankan fitur layar *mirror* (QtScrcpy).

## ⚙️ Konfigurasi
Bot membutuhkan file **`config.json`** di folder utama yang menyimpan alamat wallet tujuan, PIN, jumlah akun, dan mapping koordinat layar HP Anda. (Gunakan Menu Utama di PC untuk men-setup file ini dengan mudah).
