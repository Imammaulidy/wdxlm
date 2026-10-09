"""
Multi-Chain EVM Wallet Transfer Engine (Elastic Architecture)
============================================================
Mengelola saldo Native Gas (ETH, POL, BNB, dll) dan Token ERC-20 (USDC)
secara elastis pada berbagai jaringan EVM:
- Base Network (Coinbase L2) [Default]
- Morph L2
- Arbitrum One
- Polygon PoS
- BNB Smart Chain (BSC)
- Custom EVM Chain (RPC & Kontrak Kustom)

Mendukung rotasi RPC otomatis, switch chain on-the-fly, dan fallback ke pure JSON-RPC.
"""

import os
import time
from decimal import Decimal
import requests
from typing import Optional, Dict, Any, Tuple

try:
    from eth_account import Account
    HAS_ETH_ACCOUNT = True
except ImportError:
    Account = None
    HAS_ETH_ACCOUNT = False

# Daftar Preset Jaringan EVM Terverifikasi
DEFAULT_CHAINS_PRESET = {
    "base": {
        "name": "Base Network (Coinbase L2)",
        "chain_id": 8453,
        "native_symbol": "ETH",
        "rpc_urls": [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://base-rpc.publicnode.com",
            "https://1rpc.io/base"
        ],
        "explorer_tx": "https://basescan.org/tx/{tx_hash}",
        "token_usdc": {
            "contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimals": 6,
            "symbol": "USDC"
        }
    },
    "morph": {
        "name": "Morph L2",
        "chain_id": 2818,
        "native_symbol": "ETH",
        "rpc_urls": [
            "https://rpc.morphl2.io",
            "https://rpc-quicknode.morphl2.io"
        ],
        "explorer_tx": "https://explorer.morphl2.io/tx/{tx_hash}",
        "token_usdc": {
            "contract": "0xCfb1186F4e93D60E60a8bDd997427D1F33bc372B",
            "decimals": 6,
            "symbol": "USDC"
        }
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "native_symbol": "ETH",
        "rpc_urls": [
            "https://arb1.arbitrum.io/rpc",
            "https://arbitrum.llamarpc.com",
            "https://1rpc.io/arb"
        ],
        "explorer_tx": "https://arbiscan.io/tx/{tx_hash}",
        "token_usdc": {
            "contract": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "decimals": 6,
            "symbol": "USDC"
        }
    },
    "polygon": {
        "name": "Polygon PoS",
        "chain_id": 137,
        "native_symbol": "POL",
        "rpc_urls": [
            "https://polygon-rpc.com",
            "https://polygon.llamarpc.com",
            "https://1rpc.io/matic"
        ],
        "explorer_tx": "https://polygonscan.com/tx/{tx_hash}",
        "token_usdc": {
            "contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
            "decimals": 6,
            "symbol": "USDC"
        }
    },
    "bsc": {
        "name": "BNB Smart Chain (BSC)",
        "chain_id": 56,
        "native_symbol": "BNB",
        "rpc_urls": [
            "https://bsc-dataseed.binance.org",
            "https://binance.llamarpc.com",
            "https://1rpc.io/bnb"
        ],
        "explorer_tx": "https://bscscan.com/tx/{tx_hash}",
        "token_usdc": {
            "contract": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
            "decimals": 18,
            "symbol": "USDC"
        }
    }
}

def to_checksum_address(addr: str) -> str:
    """Mengubah address EVM ke format EIP-55 Checksum."""
    try:
        import eth_utils
        return eth_utils.to_checksum_address(addr)
    except Exception:
        pass
    addr_clean = addr.lower().replace("0x", "")
    try:
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(addr_clean.encode("latin1"))
        h = k.hexdigest()
        return "0x" + "".join(
            c.upper() if int(h[i], 16) >= 8 else c
            for i, c in enumerate(addr_clean)
        )
    except Exception:
        return "0x" + addr_clean


class EVMWallet:
    """
    Manajer Dompet Multi-Chain EVM Universal.
    Mendukung pengecekan saldo gas & token, serta pengiriman token secara elastis
    di chain mana pun (Base, Morph, Arbitrum, Polygon, BSC, atau Custom).
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        chain_key: str = "base",
        custom_rpc: Optional[str] = None,
        custom_chain_config: Optional[Dict[str, Any]] = None
    ):
        self.chain_key = chain_key.lower() if chain_key else "base"
        self.private_key: Optional[str] = None
        self.address: Optional[str] = None
        
        self.load_chain(self.chain_key, custom_rpc, custom_chain_config)
        
        if private_key and str(private_key).strip():
            self.set_private_key(str(private_key).strip())

    def load_chain(
        self,
        chain_key: str,
        custom_rpc: Optional[str] = None,
        custom_chain_config: Optional[Dict[str, Any]] = None
    ):
        """Memuat atau beralih ke spesifikasi rantai EVM tertentu."""
        self.chain_key = (chain_key or "base").lower()
        preset = DEFAULT_CHAINS_PRESET.get(self.chain_key, DEFAULT_CHAINS_PRESET["base"])
        
        # Gabungkan jika ada custom config
        cfg = dict(preset)
        if custom_chain_config and isinstance(custom_chain_config, dict):
            cfg.update(custom_chain_config)
            
        self.chain_name = cfg.get("name", self.chain_key.upper())
        self.chain_id = int(cfg.get("chain_id", 8453))
        self.native_symbol = cfg.get("native_symbol", "ETH")
        self.explorer_tx = cfg.get("explorer_tx", "https://basescan.org/tx/{tx_hash}")
        
        rpc_list = []
        if custom_rpc and custom_rpc.strip():
            rpc_list.append(custom_rpc.strip())
        for r in cfg.get("rpc_urls", []):
            if r not in rpc_list:
                rpc_list.append(r)
        if not rpc_list:
            rpc_list = ["https://mainnet.base.org"]
        self.rpc_urls = rpc_list

        tok_cfg = cfg.get("token_usdc", {})
        self.usdc_contract = tok_cfg.get("contract", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913").lower()
        self.usdc_decimals = int(tok_cfg.get("decimals", 6))
        self.token_symbol = tok_cfg.get("symbol", "USDC")

    def switch_chain(self, chain_key: str, custom_rpc: Optional[str] = None):
        """Beralih jaringan secara elastis on-the-fly."""
        self.load_chain(chain_key, custom_rpc=custom_rpc)
        return self.get_chain_info()

    def get_chain_info(self) -> Dict[str, Any]:
        """Mengembalikan metadata ringkas tentang jaringan aktif."""
        return {
            "chain_key": self.chain_key,
            "name": self.chain_name,
            "chain_id": self.chain_id,
            "native_symbol": self.native_symbol,
            "token_symbol": self.token_symbol,
            "contract": self.usdc_contract,
            "decimals": self.usdc_decimals,
            "active_rpc": self.rpc_urls[0] if self.rpc_urls else "-"
        }

    def set_private_key(self, pk: str):
        """Memuat akun dari Private Key."""
        pk_clean = pk.strip()
        if not pk_clean.startswith("0x"):
            pk_clean = "0x" + pk_clean
        self.private_key = pk_clean
        if HAS_ETH_ACCOUNT:
            acct = Account.from_key(pk_clean)
            self.address = acct.address
            return True, self.address
        return False, "eth_account library not installed"

    def _rpc_call(self, method: str, params: list) -> Tuple[bool, Any]:
        """Menjalankan pemanggilan JSON-RPC ke node dengan rotasi otomatis jika terjadi gangguan."""
        last_err = "RPC Error"
        for rpc in self.rpc_urls:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                }
                r = requests.post(rpc, json=payload, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if "result" in data:
                        return True, data["result"]
                    if "error" in data:
                        last_err = data["error"].get("message", "RPC Error")
            except Exception as e:
                last_err = str(e)
                continue
        return False, f"Semua node RPC {self.chain_name} gagal dihubungi ({last_err})"

    def get_balances(self, target_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Mengambil saldo Native Gas (ETH/POL/BNB) dan Token USDC pada jaringan aktif.
        """
        addr = (target_address or self.address or "").strip()
        if not addr or not addr.startswith("0x") or len(addr) != 42:
            return {"success": False, "error": f"Address EVM tidak valid: {addr}"}

        # 1. Cek Saldo Native Gas
        eth_bal = 0.0
        ok_gas, res_gas = self._rpc_call("eth_getBalance", [addr, "latest"])
        if ok_gas and isinstance(res_gas, str):
            wei_val = int(res_gas, 16)
            eth_bal = float(wei_val) / 10**18

        # 2. Cek Token USDC (Contract: balanceOf)
        usdc_bal = 0.0
        addr_padded = addr.lower().replace("0x", "").zfill(64)
        call_data = "0x70a08231" + addr_padded
        ok_tok, res_tok = self._rpc_call("eth_call", [{"to": self.usdc_contract, "data": call_data}, "latest"])
        if ok_tok and isinstance(res_tok, str):
            raw_val = int(res_tok, 16)
            usdc_bal = float(raw_val) / (10 ** self.usdc_decimals)

        return {
            "success": True,
            "address": addr,
            "eth_balance": eth_bal,
            "gas_balance": eth_bal,
            "native_symbol": self.native_symbol,
            "usdc_balance": usdc_bal,
            "token_symbol": self.token_symbol,
            "chain_id": self.chain_id,
            "network": self.chain_name,
            "chain_key": self.chain_key
        }

    def get_eth_balance(self, target_address: Optional[str] = None) -> float:
        """Mengambil saldo native gas (ETH/POL/BNB)."""
        res = self.get_balances(target_address)
        return res.get("eth_balance", 0.0) if res.get("success") else 0.0

    def get_usdc_balance(self, target_address: Optional[str] = None) -> float:
        """Mengambil saldo token USDC pada chain aktif."""
        res = self.get_balances(target_address)
        return res.get("usdc_balance", 0.0) if res.get("success") else 0.0

    def send_usdc(self, to_address: str, amount_usdc: float) -> Dict[str, Any]:
        """
        Mengirim Token USDC dari Wallet Tebar ke alamat tuyul pada rantai aktif.
        """
        return self.send_token(to_address, amount_usdc)

    def send_token(self, to_address: str, amount: float) -> Dict[str, Any]:
        """
        Mengirim Token ERC-20 pada jaringan EVM aktif.
        """
        try:
            if not self.private_key or not self.address:
                return {"success": False, "error": "Private key wallet tebar belum diatur!"}

            if not HAS_ETH_ACCOUNT:
                return {"success": False, "error": "Library eth_account belum tersedia"}

            to_addr = to_address.strip()
            if not to_addr.startswith("0x") or len(to_addr) != 42:
                return {"success": False, "error": f"Alamat tujuan tidak valid: {to_addr}"}

            amount_dec = Decimal(str(amount))
            amount_raw = int(amount_dec * (Decimal(10) ** self.usdc_decimals))
            if amount_raw <= 0:
                return {"success": False, "error": "Jumlah transfer harus lebih dari 0"}

            # 1. Periksa Saldo Wallet Pengirim
            bals = self.get_balances(self.address)
            if not bals.get("success"):
                return {"success": False, "error": f"Gagal mengecek saldo wallet pengirim: {bals.get('error')}"}

            if bals["usdc_balance"] < float(amount_dec):
                return {
                    "success": False,
                    "error": f"Saldo {self.token_symbol} {self.chain_name} tidak cukup! Tersedia: {bals['usdc_balance']:.4f} {self.token_symbol}, Butuh: {amount:.4f} {self.token_symbol}"
                }

            if bals["gas_balance"] < 0.00001:
                return {
                    "success": False,
                    "error": f"Saldo gas {self.native_symbol} ({self.chain_name}) tidak cukup untuk bayar fee transaksi! Saldo Gas: {bals['gas_balance']:.6f} {self.native_symbol}"
                }

            # 2. Ambil Nonce Pengirim
            ok_nonce, res_nonce = self._rpc_call("eth_getTransactionCount", [self.address, "pending"])
            if not ok_nonce:
                return {"success": False, "error": f"Gagal membaca nonce transaksi: {res_nonce}"}
            nonce = int(res_nonce, 16)

            # 3. Ambil Gas Price Dinamis
            ok_gp, res_gp = self._rpc_call("eth_gasPrice", [])
            gas_price = int(res_gp, 16) if ok_gp else 100000000  # 0.1 gwei fallback
            # Berikan buffer gas price 20% agar transaksi diprioritaskan
            gas_price_boosted = max(int(gas_price * 1.20), 10000000)
            gas_limit = 95000

            # 4. Susun Calldata ERC20 transfer(address,uint256) (0xa9059cbb)
            to_clean = to_addr.lower().replace("0x", "").zfill(64)
            amt_hex = hex(amount_raw)[2:].zfill(64)
            tx_data = "0xa9059cbb" + to_clean + amt_hex

            tx_dict = {
                "to": to_checksum_address(self.usdc_contract),
                "value": 0,
                "gas": gas_limit,
                "gasPrice": gas_price_boosted,
                "nonce": nonce,
                "chainId": self.chain_id,
                "data": bytes.fromhex(tx_data[2:])
            }

            # 5. Sign Transaksi EIP-155
            try:
                signed = Account.sign_transaction(tx_dict, self.private_key)
                raw_tx = getattr(signed, 'rawTransaction', getattr(signed, 'raw_transaction', None))
                if raw_tx is None:
                    return {"success": False, "error": "Gagal membaca raw transaction dari signed transaction"}
                raw_hex = raw_tx.hex() if hasattr(raw_tx, 'hex') else str(raw_tx)
                if not raw_hex.startswith("0x"):
                    raw_hex = "0x" + raw_hex
                raw_tx_hex = raw_hex
            except Exception as e:
                return {"success": False, "error": f"Gagal menandatangani transaksi: {e}"}

            # 6. Broadcast Transaksi ke Node RPC
            ok_send, res_send = self._rpc_call("eth_sendRawTransaction", [raw_tx_hex])
            if not ok_send:
                return {"success": False, "error": f"Gagal broadcast transaksi ke {self.chain_name}: {res_send}"}

            tx_hash = res_send
            explorer_link = self.explorer_tx.format(tx_hash=tx_hash)
            print(f"[V] Transaksi {self.token_symbol} ({self.chain_name}) terkirim! TxHash: {tx_hash}")
            print(f"[*] Explorer: {explorer_link}")

            # 7. Tunggu Konfirmasi On-Chain (Receipt)
            print(f"[*] Menunggu konfirmasi blok di jaringan {self.chain_name}...")
            confirmed = False
            for _ in range(25):
                time.sleep(2)
                ok_rec, res_rec = self._rpc_call("eth_getTransactionReceipt", [tx_hash])
                if ok_rec and isinstance(res_rec, dict) and res_rec.get("blockNumber"):
                    status = int(res_rec.get("status", "0x0"), 16)
                    confirmed = (status == 1)
                    break

            return {
                "success": True,
                "tx_hash": tx_hash,
                "explorer": explorer_link,
                "amount": amount,
                "to_address": to_addr,
                "network": self.chain_name,
                "token_symbol": self.token_symbol,
                "confirmed": confirmed
            }
        except Exception as e:
            return {"success": False, "error": f"Kesalahan saat proses kirim token: {e}"}


# Aliases untuk kompatibilitas ke modul-modul lain
BaseWallet = EVMWallet
MorphWallet = EVMWallet
BASE_CONFIG = DEFAULT_CHAINS_PRESET["base"]
MORPH_CONFIG = DEFAULT_CHAINS_PRESET["morph"]
