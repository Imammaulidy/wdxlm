# 🚀 BITGET WALLET TOOLS (WD XLM & QRIS MORPH L2)

Otomasi cerdas multi-fitur untuk Withdraw (WD) XLM Massal, Auto Create Akun Bitget Wallet, dan Bot QRIS Cashback Multi-Chain EVM via ADB Android.

---

## 📱 Panduan Termux (Android) - Copy & Paste Ready

Jalankan perintah berikut di aplikasi Termux:

```bash
# 1. Update sistem & install paket dasar
pkg update -y && pkg install git python android-tools curl unzip nmap -y

# 2. Clone repositori
git clone https://github.com/Imammaulidy/wdxlm.git
cd wdxlm

# 3. Install dependensi Python
pip install -r Core/requirements.txt

# 4. Jalankan bot (Interactive Menu)
bash run.sh
```

---

## 💻 Panduan Windows (PC / Laptop) - Copy & Paste Ready

Persyaratan: [Python 3.10+](https://www.python.org/) (Centang *Add Python to PATH*) & [Git](https://git-scm.com/).

```cmd
:: 1. Clone repositori
git clone https://github.com/Imammaulidy/wdxlm.git
cd wdxlm

:: 2. Jalankan All-in-One Launcher (Auto-Elevasi UAC Administrator & Auto .venv)
START BOT.bat
```

> **Catatan Windows**: Cukup double-click `START BOT.bat` di File Explorer. Script otomatis membuat `.venv`, menginstal dependensi, serta menyediakan Control Panel interaktif untuk WD XLM, Bot QRIS, Web Dashboard, PM2, dan reset ADB.

---

## ⚡ Fitur Inti & Solusi Masalah

| Fitur | Deskripsi | Shortcut |
| :--- | :--- | :--- |
| **WD XLM Massal** | Tarik XLM otomatis (Mode Baru Impor Profil / Mode Old Authenticator) | Menu `[1]` / `bash run.sh --wd` |
| **Bot QRIS Morph L2** | Automasi scan & payment QRIS cashback multi-chain | Menu `[2]` / `bash run.sh --qris` |
| **Web Dashboard** | Web controller modern di Port 2000 (dukungan LAN & Cloudflare Tunnel) | Menu `[3]` / `[4]` |
| **Service PM2 Background** | Manajemen background service 24/7 terisolasi (`bitget-server`) | Menu `[4]`, `[5]`, `[6]` |
| **Reset ADB Daemon** | Bersihkan port 5037/5555 dan restart adb server jika device macet | Menu `[7]` |

> 💡 **Troubleshooting Cepat**: Jika device tidak terdeteksi, aktifkan **USB Debugging** (atau Wireless Debugging) dan jalankan menu `[7]` di Windows atau menu `[6]` di Termux. File konfigurasi dibuat otomatis dari `Core/Json/config.example.json` saat pertama kali dijalankan.
