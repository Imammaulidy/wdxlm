"""
Morph L2 USDC Wallet Transfer Engine (Standalone)
=================================================
Mengelola saldo dan pengiriman USDC pada jaringan Morph L2 (Chain ID: 2818)
dari Wallet Tebar ke alamat wallet tuyul / garapan.
Mendukung Web3 dan Fallback Pure JSON-RPC via requests + eth_account.
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

# Konfigurasi Jaringan Morph L2
MORPH_CONFIG = {
    "name": "Morph Network",
    "chain_id": 2818,
    "rpc_urls": [
        "https://rpc.morphl2.io",
        "https://rpc-quicknode.morphl2.io",
        "https://morph-mainnet.blastapi.io"
    ],
    "native_symbol": "ETH",
    "explorer_tx": "https://explorer.morphl2.io/tx/{tx_hash}",
    "token_usdc": {
        "contract": "0xCfb1186F4e93D60E60a8bDd997427D1F33bc372B",
        "decimals": 6,
        "symbol": "USDC"
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

class MorphWallet:
    """Manajer Wallet EVM Morph L2 untuk Cek Saldo & Transfer Token USDC."""

    def __init__(self, private_key: Optional[str] = None, custom_rpc: Optional[str] = None):
        self.rpc_urls = [custom_rpc] if custom_rpc else MORPH_CONFIG["rpc_urls"]
        self.chain_id = MORPH_CONFIG["chain_id"]
        self.usdc_contract = MORPH_CONFIG["token_usdc"]["contract"].lower()
        self.usdc_decimals = MORPH_CONFIG["token_usdc"]["decimals"]
        
        self.private_key = None
        self.address = None
        if private_key and private_key.strip():
            self.set_private_key(private_key.strip())

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
        """Menjalankan pemanggilan JSON-RPC ke node Morph dengan rotasi otomatis."""
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
                        return False, data["error"].get("message", "RPC Error")
            except Exception:
                continue
        return False, "Semua node RPC Morph tidak merespon"

    def get_balances(self, target_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Mengambil saldo Native ETH (gas) dan Token USDC pada jaringan Morph L2.
        """
        addr = (target_address or self.address or "").strip()
        if not addr or not addr.startswith("0x") or len(addr) != 42:
            return {"success": False, "error": f"Address EVM tidak valid: {addr}"}

        # 1. Cek Native ETH (Gas)
        eth_bal = 0.0
        ok_eth, res_eth = self._rpc_call("eth_getBalance", [addr, "latest"])
        if ok_eth and isinstance(res_eth, str):
            wei_val = int(res_eth, 16)
            eth_bal = float(wei_val) / 10**18

        # 2. Cek Token USDC (Contract: balanceOf)
        usdc_bal = 0.0
        # Method id balanceOf(address): 0x70a08231 + padded address
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
            "usdc_balance": usdc_bal,
            "chain_id": self.chain_id,
            "network": "Morph L2"
        }

    def send_usdc(self, to_address: str, amount_usdc: float) -> Dict[str, Any]:
        """
        Mengirim Token USDC Morph dari Wallet Tebar ke alamat target.
        """
        try:
            if not self.private_key or not self.address:
                return {"success": False, "error": "Private key wallet tebar belum diatur!"}

            if not HAS_ETH_ACCOUNT:
                return {"success": False, "error": "Library eth_account belum tersedia"}

            to_addr = to_address.strip()
            if not to_addr.startswith("0x") or len(to_addr) != 42:
                return {"success": False, "error": f"Alamat tujuan tidak valid: {to_addr}"}

            amount_dec = Decimal(str(amount_usdc))
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
                    "error": f"Saldo USDC Morph tidak cukup! Tersedia: {bals['usdc_balance']:.4f} USDC, Butuh: {amount_usdc:.4f} USDC"
                }

            if bals["eth_balance"] < 0.00005:
                return {
                    "success": False,
                    "error": f"Saldo gas ETH Morph tidak cukup untuk bayar fee transaksi! Saldo ETH: {bals['eth_balance']:.6f} ETH"
                }

            # 2. Ambil Nonce Pengirim
            ok_nonce, res_nonce = self._rpc_call("eth_getTransactionCount", [self.address, "pending"])
            if not ok_nonce:
                return {"success": False, "error": f"Gagal membaca nonce transaksi: {res_nonce}"}
            nonce = int(res_nonce, 16)

            # 3. Ambil Gas Price
            ok_gp, res_gp = self._rpc_call("eth_gasPrice", [])
            gas_price = int(res_gp, 16) if ok_gp else 2000000
            gas_price_boosted = max(int(gas_price * 1.25), 2000000)
            gas_limit = 100000

            # 4. Susun Calldata ERC20 transfer(address,uint256)
            # transfer(address,uint256) signature = 0xa9059cbb
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

            # 5. Sign Transaksi
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

            # 6. Broadcast Transaksi
            ok_send, res_send = self._rpc_call("eth_sendRawTransaction", [raw_tx_hex])
            if not ok_send:
                return {"success": False, "error": f"Gagal broadcast transaksi ke Morph: {res_send}"}

            tx_hash = res_send
            explorer_link = MORPH_CONFIG["explorer_tx"].format(tx_hash=tx_hash)
            print(f"[V] Transaksi USDC Morph terkirim! TxHash: {tx_hash}")
            print(f"[*] Explorer: {explorer_link}")

            # 7. Tunggu Konfirmasi On-Chain (Receipt)
            print("[*] Menunggu konfirmasi blok di jaringan Morph L2...")
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
                "amount": amount_usdc,
                "to_address": to_addr,
                "confirmed": confirmed
            }
        except Exception as e:
            return {"success": False, "error": f"Kesalahan saat proses kirim USDC: {e}"}
