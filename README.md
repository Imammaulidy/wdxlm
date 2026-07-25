# Auto WD XLM Bitget Wallet
Bot otomatisasi untuk melakukan Withdraw (WD) XLM secara massal dari banyak akun kloningan Bitget Wallet menggunakan ADB (Android Debug Bridge).

## 🚀 Fitur Utama
- **Interaktif CLI:** Memiliki Menu Utama interaktif bergaya terminal.
- **PIN Dinamis:** Tidak perlu *hardcode* kordinat layar lagi. Ubah PIN sesuka hati lewat menu, dan bot akan menghitung ketukan layar berdasarkan koordinat dinamis.
- **Support Termux & Windows:** Dapat dijalankan dari laptop (Windows) menggunakan kabel USB, maupun mode nirkabel murni langsung dari HP via Termux.
- **Otomatisasi Penuh:**
  1. Berpindah antar clone akun di aplikasi *Multi App*.
  2. WD XLM Max Amount secara otomatis.
  3. Mengambil OTP dari aplikasi Google Authenticator.
  4. Mengatur input PIN pola keamanan secara dinamis.
  5. *Kill apps* setelah selesai.

## 🛠️ Persyaratan
- **Windows / PC:** Terinstal Python 3 dan ADB.
- **Termux (Android):** Terinstal Python, `android-tools` (ADB), dan termux-api.
- **Aplikasi Pendukung di HP Android:**
  - Multi App Ultra (Untuk clone Bitget)
  - Bitget Wallet
  - Google Authenticator

## 📥 Instalasi
### Instalasi di Termux (Android Tanpa PC)
Jalankan script bash installer berikut di Termux:
```bash
./setup_termux.sh
```

### Instalasi di Windows
1. Buka CMD/Terminal.
2. Install modul Python:
```cmd
pip install -r requirements.txt
```

## ⚙️ Konfigurasi
Anda wajib membuat file `config.json` di root direktori (atau salin dari `config.example.json`). File ini menyimpan alamat wallet tujuan, PIN, jumlah akun, dan mapping koordinat layar HP Anda.

## ▶️ Cara Menjalankan
Cukup buka **`MENU_UTAMA.bat`** (jika di Windows) atau jalankan `python menu.py` di Termux untuk mengakses layar interaktif.
