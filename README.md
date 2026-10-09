# 🚀 BOT AUTO WD XLM, CREATOR BITGET & QRIS MULTI-CHAIN EVM (ADB STANDALONE)

Ekosistem otomasi cerdas untuk **Withdraw (WD) XLM Massal**, **Pembuatan Akun Dompet Baru (Create Account)**, dan **Bot QRIS Payment & Tebar Saldo Multi-Chain EVM (Base / Morph / Arbitrum / Polygon / BSC)** dari Bitget Wallet menggunakan ADB Android.

---

## ⚡ SHORTCUT MENJALANKAN BOT

### 🌐 1. Mode Web UI Dashboard (Rekomendasi PC):
Double-click **`WEB_UI.bat`** di Windows. Browser otomatis terbuka di:
👉 **`http://127.0.0.1:5000`**

### 💎 2. Mode Bot QRIS & Multi-Chain EVM (Base / Morph):
Double-click **`GAS QRIS MORPH.bat`** atau jalankan via terminal:
```bash
python core/qris_morph.py
```

### 💻 3. Mode Terminal WD XLM & Creator:
Double-click **`GAS WD.bat`** atau jalankan via terminal:
```bash
python core/menu.py
```

### 📱 4. Mode Termux (Android tanpa PC):
Jalankan runner di aplikasi Termux:
```bash
bash run.sh
```

---

## ✨ FITUR UTAMA SISTEM

### 🔗 1. Dompet Tebar Multi-Chain EVM (Universal & Elastic):
- **Bebas Pilih Jaringan (Multi-Chain Switcher):**
  - **Base Network (Coinbase L2)** — *Default* (Chain ID: `8453`, Gas: `ETH`, Token: `USDC`)
  - **Morph L2** (Chain ID: `2818`, Gas: `ETH`, Token: `USDC`)
  - **Arbitrum One** (Chain ID: `42161`, Gas: `ETH`, Token: `USDC`)
  - **Polygon PoS** (Chain ID: `137`, Gas: `POL`, Token: `USDC`)
  - **BNB Smart Chain (BSC)** (Chain ID: `56`, Gas: `BNB`, Token: `USDC`)
  - **Custom EVM Network** — Bebas tentukan Chain ID, Custom RPC URL, dan Kontrak Token ERC-20.
- **Pengecekan Saldo Real-Time:** Membaca saldo Native Gas (ETH/POL/BNB) dan Token ERC-20 (USDC) langsung dari node on-chain.
- **Transfer Otomatis ke Alamat Tuyul:** Melakukan transfer token dari wallet tebar ke dompet sasaran secara instan sesuai kebutuhan layar Bitget Wallet.
- **Auto-Failover RPC:** Dilengkapi rotasi multi-node RPC publik untuk menjamin keandalan koneksi saat broadcast transaksi.

### 💳 2. Bot QRIS GoBiz Dinamis & Multi-Akun Rotasi:
- **Multi-Account Shift Rotation:** Mendukung penambahan multi akun GoBiz dengan mode rotasi bergantian (*selang-seling shift*) tiap satu siklus transaksi.
- **Auto Push QR ke HP:** Gambar QRIS digenerate secara on-the-fly dan langsung dikirim ke memori internal HP (`/sdcard/Download/qris_pay.png`).
- **Penyalinan Alamat Tuyul Otomatis:** Membaca alamat EVM deposit Bitget Wallet tuyul via clipboard / UI dump dan menyimpannya ke memori bot.

### 🛡️ 3. Reset Identitas Clone & GAID Presisi:
- **Pembersihan Cache & Force Stop:** Menghentikan dan membersihkan cache aplikasi kloningan (Dual Space / Multi App).
- **Alur Baru Reset GAID (Google Advertising ID):**
  - Delete advertising ID -> Confirm -> Get new advertising ID -> Confirm -> Reset advertising ID -> Confirm.
- **Reset IP Jaringan (Mode Pesawat 3s):** Mematikan koneksi sesaat untuk mendapatkan alokasi IP baru sebelum membuka clone Bitget.

### 📐 4. Zero-Factory-Reset Screen Protection:
- Merekam resolusi & DPI asli perangkat saat bot dijalankan.
- Mengatur ukuran kerja bot (`1080x2400 @ 352 DPI`).
- Mengembalikan resolusi asli HP secara mulus saat bot selesai atau ditutup (tanpa perintah berbahaya `wm size reset` / `wm density reset`).

---

## 🛠️ PERSYARATAN SISTEM

### 📱 Di HP Android:
1. **Dual Space** (`com.xunijun.app.gp`) atau **Multi App Ultra** (`com.waxmoon.ma.gp`).
2. **Bitget Wallet** terinstall di dalam aplikasi clone.
3. **Opsi Pengembang (Developer Options):**
   - Aktifkan *Debugging USB* (untuk PC).
   - Aktifkan *Proses Debug Nirkabel* / *Wireless Debugging* (jika menggunakan koneksi Wi-Fi/Termux).

### 💻 Di PC / Windows:
- Python 3.8+ (`pip install -r requirements.txt` atau minimal `requests`, `eth-account`, `flask`).
- Driver ADB & scrcpy sudah disertakan di folder `core/`.

---

## ⚙️ STRUKTUR KONFIGURASI (`core/config.json`)

Contoh file template tersedia pada [`core/config.example.json`](core/config.example.json):

```json
{
    "active_chain": "base",
    "chains": {
        "base": {
            "name": "Base Network (Coinbase L2)",
            "chain_id": 8453,
            "native_symbol": "ETH",
            "rpc_url": "https://mainnet.base.org",
            "usdc_contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        },
        "morph": {
            "name": "Morph L2",
            "chain_id": 2818,
            "native_symbol": "ETH",
            "rpc_url": "https://rpc.morphl2.io",
            "usdc_contract": "0xCfb1186F4e93D60E60a8bDd997427D1F33bc372B"
        }
    },
    "wallet_tebar": {
        "address": "0x26450eAA15C681Db5eBF3d9823B64D98D9ccD7BF",
        "private_key": "0xYOUR_PRIVATE_KEY_HERE"
    },
    "default_qris_nominal": 10500,
    "usdc_buffer": 0.0,
    "fallback_rate": 17400,
    "gobiz_accounts": [
        {
            "merchant_id": "G000000001",
            "auth_token": "YOUR_TOKEN_1",
            "merchant_name": "MERCHANT 1"
        },
        {
            "merchant_id": "G000000002",
            "auth_token": "YOUR_TOKEN_2",
            "merchant_name": "MERCHANT 2"
        }
    ],
    "gobiz_shift_rotation": true
}
```

---

## 🔒 KEAMANAN & PRIVASI (GIT SANITIZATION)
Proyek ini mematuhi standar sanitasi keamanan ketat:
- Seluruh kredensial pribadi, private key, token GoBiz, email OTP, serta file database transaksi lokal dilindungi secara otomatis melalui [`.gitignore`](.gitignore) dan tidak akan pernah ter-push ke repository publik.
