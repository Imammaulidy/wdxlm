#!/bin/bash
# ==============================================================================
# SETUP OTOMATIS 1-KLIK SHIZUKU (rish) UNTUK TERMUX (NON-ROOT & OFFLINE)
# Standar Arsitektur: termux-shizuku-adb (Bypass Scoped Storage & Android 14+ DEX)
# ==============================================================================

echo "========================================================="
echo "   INSTALLER SHIZUKU (rish) NON-ROOT UNTUK TERMUX        "
echo "========================================================="

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
mkdir -p "$PREFIX_DIR/bin" "$PREFIX_DIR/lib" "$PREFIX_DIR/tmp"

export RISH_APPLICATION_ID="com.termux"
export LD_LIBRARY_PATH="$PREFIX_DIR/lib:$LD_LIBRARY_PATH"

# 1. Simpan konfigurasi ke ~/.bashrc jika belum ada
grep -q "RISH_APPLICATION_ID" "$HOME/.bashrc" 2>/dev/null || echo 'export RISH_APPLICATION_ID="com.termux"' >> "$HOME/.bashrc"
grep -q "LD_LIBRARY_PATH" "$HOME/.bashrc" 2>/dev/null || echo "export LD_LIBRARY_PATH=\"$PREFIX_DIR/lib:\$LD_LIBRARY_PATH\"" >> "$HOME/.bashrc"

# 2. Cek apakah Shizuku APK terpasang di sistem
APK_PATH=$(pm path moe.shizuku.privileged.api 2>/dev/null | head -n 1 | cut -d: -f2)

if [ -n "$APK_PATH" ] && [ -f "$APK_PATH" ]; then
    echo "[*] Shizuku APK terdeteksi di: $APK_PATH"
    echo "[*] Mengekstrak rish, rish_shizuku.dex & librish.so dari APK..."
    unzip -o -q "$APK_PATH" "assets/rish" "assets/rish_shizuku.dex" "lib/*/librish.so" -d "$PREFIX_DIR/tmp" 2>/dev/null
    
    if [ -f "$PREFIX_DIR/tmp/assets/rish" ]; then
        mv "$PREFIX_DIR/tmp/assets/rish" "$PREFIX_DIR/bin/rish"
        mv "$PREFIX_DIR/tmp/assets/rish_shizuku.dex" "$PREFIX_DIR/bin/rish_shizuku.dex"
        find "$PREFIX_DIR/tmp" -name "librish.so" -exec cp {} "$PREFIX_DIR/lib/librish.so" \; 2>/dev/null
        find "$PREFIX_DIR/tmp" -name "librish.so" -exec cp {} "$PREFIX_DIR/bin/librish.so" \; 2>/dev/null
        rm -rf "$PREFIX_DIR/tmp/assets" "$PREFIX_DIR/tmp/lib"
        echo "[+] Berhasil mengekstrak file rish dari APK lokal!"
    fi
fi

# Fallback unduh jika ekstraksi APK gagal atau file belum ada
if [ ! -f "$PREFIX_DIR/bin/rish" ] || [ ! -f "$PREFIX_DIR/bin/rish_shizuku.dex" ]; then
    echo "[*] Mengunduh rish dari repositori resmi RikkaApps Shizuku-API..."
    curl -sL "https://raw.githubusercontent.com/RikkaApps/Shizuku-API/master/rish/rish" -o "$PREFIX_DIR/bin/rish"
    curl -sL "https://raw.githubusercontent.com/RikkaApps/Shizuku-API/master/rish/rish_shizuku.dex" -o "$PREFIX_DIR/bin/rish_shizuku.dex"
fi

# 3. Patch Package ID ke com.termux agar izin binder dikenali Shizuku
if [ -f "$PREFIX_DIR/bin/rish" ]; then
    sed -i 's/"PKG"/"com.termux"/g' "$PREFIX_DIR/bin/rish" 2>/dev/null
    sed -i 's/export RISH_APPLICATION_ID="PKG"/export RISH_APPLICATION_ID="com.termux"/g' "$PREFIX_DIR/bin/rish" 2>/dev/null
    sed -i 's/PKG/com.termux/g' "$PREFIX_DIR/bin/rish" 2>/dev/null
fi

# 4. Beri izin eksekusi untuk binary dan izin READ-ONLY untuk DEX (Wajib Android 14+)
chmod 755 "$PREFIX_DIR/bin/rish" 2>/dev/null
chmod 400 "$PREFIX_DIR/bin/rish_shizuku.dex" 2>/dev/null || chmod 444 "$PREFIX_DIR/bin/rish_shizuku.dex" 2>/dev/null

echo "========================================================="
echo "[*] Menguji koneksi rish..."
if command -v rish &> /dev/null; then
    TEST_RES=$(rish -c "id" 2>&1)
    if echo "$TEST_RES" | grep -q "uid=2000"; then
        echo "[+] SUKSES BESAR! Shizuku (rish) AKTIF SEMPURNA!"
        echo "    $TEST_RES"
        echo "[+] Bot sekarang bisa berjalan offline tanpa Wi-Fi / Hotspot!"
    else
        echo "[-] Hasil uji: $TEST_RES"
        echo "[!] CATATAN PENTING:"
        echo "    1. Buka aplikasi Shizuku di HP, pastikan status: 'Shizuku is running'."
        echo "    2. Jika muncul pop-up izin 'Allow Termux to access Shizuku?', klik 'Always allow'."
    fi
else
    echo "[-] Binary rish belum terdeteksi di PATH."
fi
echo "========================================================="
