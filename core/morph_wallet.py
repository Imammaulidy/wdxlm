"""
Base Network USDC Wallet Transfer Engine (Alias / Wrapper)
===========================================================
Mengalihkan ke modul base_wallet.py untuk jaringan Base Mainnet (Chain ID: 8453).
"""

from base_wallet import BaseWallet, BASE_CONFIG, to_checksum_address

# Alias kompatibilitas
MorphWallet = BaseWallet
MORPH_CONFIG = BASE_CONFIG
