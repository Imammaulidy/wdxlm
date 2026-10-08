import os
import re
import sys
import json
import subprocess
from typing import List, Dict, Optional, Tuple

CORE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CORE_DIR, '..'))
WALLET_DIR = os.path.join(PROJECT_ROOT, 'DATA WALLET BITGET')
CONFIG_FILE = os.path.join(CORE_DIR, 'config.json')

def get_available_wallet_files() -> List[str]:
    """Mengambil daftar nama file .txt di folder DATA WALLET BITGET."""
    if not os.path.exists(WALLET_DIR):
        return []
    files = [f for f in os.listdir(WALLET_DIR) if f.lower().endswith('.txt')]
    # Urutkan file berdasarkan waktu modifikasi terbaru
    files.sort(key=lambda x: os.path.getmtime(os.path.join(WALLET_DIR, x)), reverse=True)
    return files

def parse_wallet_phrase_line(raw_line: str) -> Optional[Dict[str, str]]:
    """
    Mengekstrak 12 kata mnemonic seed phrase & referral code opsional dari satu baris teks.
    Contoh input:
      - '1. word_one word_two word_three word_four word_five word_six word_seven word_eight word_nine word_ten word_eleven word_twelve'
      - 'kata_1 kata_2 kata_3 kata_4 kata_5 kata_6 kata_7 kata_8 kata_9 kata_10 kata_11 kata_12 (Ref: ABCDEFGH)'
    """
    line = raw_line.strip()
    if not line:
        return None

    # Ekstrak referral code jika ada
    ref_match = re.search(r'\(Ref:\s*([a-zA-Z0-9]+)\)', line, re.IGNORECASE)
    ref_code = ref_match.group(1).strip() if ref_match else ""

    # Ekstrak nomor baris/urut di depan jika ada (misal "1.", "1)", "10 - ")
    num_match = re.match(r'^(\d+)[\.\)\-]?', line)
    raw_num = num_match.group(1) if num_match else ""

    # Hapus nomor baris di depan
    clean = re.sub(r'^\d+[\.\)\-]?\s*', '', line)
    # Hapus bagian (Ref: ...)
    clean = re.sub(r'\(Ref:.*?\)', '', clean, flags=re.IGNORECASE).strip()

    # Ekstrak kata-kata (hanya huruf a-z)
    words = re.findall(r'[a-zA-Z]+', clean)
    if len(words) >= 12:
        phrase_12 = " ".join([w.lower() for w in words[:12]])
        return {
            "phrase": phrase_12,
            "ref_code": ref_code,
            "raw_num": raw_num,
            "raw": line
        }
    return None

def load_wallet_phrases(filename: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Memuat seluruh seed phrase dari file tertentu di DATA WALLET BITGET.
    Jika filename tidak diberikan, mengambil file yang tercatat di config.json atau file terbaru.
    """
    available = get_available_wallet_files()
    if not available:
        return []

    target_file = filename
    if not target_file:
        # Cek dari config.json
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    target_file = cfg.get("active_wallet_file")
            except Exception:
                target_file = None

    if not target_file or target_file not in available:
        target_file = available[0]

    filepath = os.path.join(WALLET_DIR, target_file)
    results = []
    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, start=1):
            parsed = parse_wallet_phrase_line(line)
            if parsed:
                parsed["index"] = len(results) + 1
                parsed["source_file"] = target_file
                results.append(parsed)

    return results

def get_phrase_by_index(index: int, filename: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Mengambil seed phrase berdasarkan urutan akun (1-indexed).
    Contoh: index=1 mengambil akun ke-1.
    """
    phrases = load_wallet_phrases(filename)
    if not phrases:
        return None
    # Jika index melebihi total akun, gunakan modul/kembalikan None
    idx_lookup = index - 1
    if 0 <= idx_lookup < len(phrases):
        return phrases[idx_lookup]
    return None

def copy_phrase_to_clipboard(phrase: str) -> bool:
    """
    Menyalin 12 kata frasa ke Windows clipboard (yang otomatis disinkronkan oleh scrcpy ke HP),
    serta mencoba menyetel clipboard Android jika memungkinkan.
    """
    if not phrase:
        return False

    success = False
    # 1. Set Windows Clipboard via PowerShell (Scrcpy syncs this directly)
    if sys.platform == "win32":
        try:
            # Gunakan subprocess PowerShell dengan aman
            clean_phrase = phrase.replace("'", "''")
            cmd = f"Set-Clipboard -Value '{clean_phrase}'"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=3)
            success = True
        except Exception:
            pass

    # 2. Set Android Clipboard via ADB jika scrcpy clipper aktif
    try:
        adb_serial = os.environ.get("ANDROID_SERIAL")
        adb_prefix = f"adb -s {adb_serial} " if adb_serial else "adb "
        # Kirim broadcast ke Clipper jika terpasang di HP
        subprocess.run(
            f'{adb_prefix}shell am broadcast -a clipper.set -e text "{phrase}"',
            shell=True,
            capture_output=True,
            timeout=2
        )
    except Exception:
        pass

    return success
