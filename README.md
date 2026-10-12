# 🚀 BOT AUTO WD XLM, CREATOR BITGET & QRIS MULTI-CHAIN

Ekosistem otomasi cerdas berkinerja tinggi untuk Withdraw (WD) XLM Massal, Pembuatan Akun Dompet Bitget Baru, dan Bot QRIS Payment & Multi-Chain EVM (Base / Morph / Arbitrum / Polygon / BSC) via ADB Android.

---

## 📱 Instalasi & Penggunaan di Termux (Android)

Buka aplikasi Termux Anda, lalu jalankan perintah di bawah ini secara berurutan:

1. Update sistem dan install paket yang dibutuhkan:
```bash
pkg update -y && pkg upgrade -y
pkg install git python android-tools curl unzip nmap -y
```

2. Clone repositori ini:
```bash
git clone https://github.com/Imammaulidy/wdxlm.git
cd wdxlm
```

3. Install dependensi Python:
```bash
pip install -r requirements.txt
```

4. Jalankan Bot:
```bash
bash run.sh
```

Gunakan tombol `Ctrl + C` (atau tekan `Volume Bawah + C`) untuk menghentikan bot.

---

## 💻 Instalasi & Penggunaan di Windows (PC/Laptop)

1. Pastikan sudah menginstall [Python 3](https://www.python.org/) (wajib centang **Add Python to PATH** saat instalasi) dan [Git](https://git-scm.com/).
2. Hubungkan HP Android ke PC via kabel USB dan pastikan **USB Debugging** aktif.
3. Clone repositori ini:
```cmd
git clone https://github.com/Imammaulidy/wdxlm.git
cd wdxlm
```

4. Install dependensi Python:
```cmd
pip install -r requirements.txt
```

5. Jalankan Bot (Pilih sesuai kebutuhan):
- **Web UI Dashboard (Browser di Port 2000 + PM2 24/7):**
  ```cmd
  GAS WEB DASHBOARD.bat
  ```
- **Bot QRIS Multi-Chain EVM (Terminal):**
  ```cmd
  GAS QRIS MORPH.bat
  ```
- **Terminal All-in-One (WD XLM & Creator Akun):**
  ```cmd
  GAS WD.bat
  ```
- **Reset ADB (Jika koneksi device macet):**
  ```cmd
  KILL_ADB.bat
  ```

---

## ⚙️ Konfigurasi Awal
File konfigurasi `core/config.json` akan otomatis dibuat dari template `core/config.example.json` saat bot pertama kali dijalankan. Anda dapat menyesuaikan PIN transaksi, delay, atau provider QRIS di file tersebut.
