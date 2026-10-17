import os
import sys

# Directory of this file: .../Core/Python
PYTHON_DIR = os.path.dirname(os.path.abspath(__file__))

# Core directory: .../Core
CORE_DIR = os.path.dirname(PYTHON_DIR)

# Project Root directory: .../SCRIPT ADB WD XLM BITGET
PROJECT_ROOT = os.path.dirname(CORE_DIR)

# Json directory: .../Core/Json
JSON_DIR = os.path.join(CORE_DIR, "Json")
os.makedirs(JSON_DIR, exist_ok=True)

# Common configuration & credential files
CONFIG_PATH = os.path.join(JSON_DIR, "config.json")
CONFIG_EXAMPLE_PATH = os.path.join(JSON_DIR, "config.example.json")
EMAILS_PATH = os.path.join(JSON_DIR, "emails.txt")
EMAILS_EXAMPLE_PATH = os.path.join(JSON_DIR, "emails.example.txt")
CREATED_ACCOUNTS_PATH = os.path.join(JSON_DIR, "created_accounts.json")
LAST_TUYUL_PATH = os.path.join(JSON_DIR, ".last_tuyul.txt")
CLOUDFLARE_TOKEN_PATH = os.path.join(JSON_DIR, "cloudflare_token.txt")

# Subdirectories inside Core
KORDINAT_DIR = os.path.join(CORE_DIR, "kordinat")
WEB_DIR = os.path.join(CORE_DIR, "web")
SCRCPY_DIR = os.path.join(CORE_DIR, "scrcpy-win64-v3.3.4")
SCRCPY_EXE = os.path.join(SCRCPY_DIR, "scrcpy.exe")
BIN_DIR = os.path.join(CORE_DIR, "bin")
DOCS_DIR = os.path.join(CORE_DIR, "docs")

# Root assets & dependencies
DATA_WALLET_DIR = os.path.join(PROJECT_ROOT, "Data Wallet Bitget")
os.makedirs(DATA_WALLET_DIR, exist_ok=True)
ECOSYSTEM_PATH = os.path.join(CORE_DIR, "ecosystem.config.js")
REQUIREMENTS_PATH = os.path.join(CORE_DIR, "requirements.txt")
VBS_CORE_PATH = os.path.join(CORE_DIR, "AUTOSTART_WINDOWS.vbs")

# Ensure Core/Python is on sys.path so any script can import other engine files directly
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)
