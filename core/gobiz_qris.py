"""
GoBiz QRIS Generator & ASPI EMVCo Modifier (Standalone)
=======================================================
Menghasilkan QRIS GoBiz dinamis resmi lengkap dengan nominal,
nama merchant acak otentik Indonesia (EMVCo Tag 59), kota (Tag 60),
serta menjaga Tag 26 (PAN GoPay) 100% UTUH agar saldo masuk tepat ke rekening merchant.
Menyimpan hasil ke file gambar PNG berkualitas tinggi untuk di-push ke HP.
"""

import os
import re
import time
import json
import uuid
import random
import string
import base64
import requests
from typing import Optional, Dict, Any, List, Tuple

try:
    import qrcode
    from PIL import Image
    HAS_QRCODE = True
except ImportError:
    qrcode = None
    Image = None
    HAS_QRCODE = False

ID_PREFIXES = [
    "WARUNG", "TOKO", "KEDAI", "DEPOT", "RM", "WARKOP", "KIOS", "FOTOCOPY",
    "LAUNDRY", "BENGKEL", "APOTEK", "AGEN", "MART", "CELL", "STORE",
    "GROSIR", "SNACK", "BAKERY", "BARBERSHOP", "SALON", "DISTRO", "VAPE",
    "PULSA", "KOPITIAM", "SERBA ADA", "SUMBER", "MITRA", "BERKAH", "ABADI",
    "MAKMUR", "SENTOSA", "SEJAHTERA", "ANUGERAH", "REJEKI", "HARAPAN",
    "UTAMA", "KARYA", "SINAR", "CAHAYA", "BINTANG", "SURYA", "FAJAR"
]

ID_BUSINESS_NAMES = [
    "BUDI", "SANTOSO", "SLAMET", "WAHYU", "AGUS", "EKO", "BAMBANG", "JOKO",
    "HENDRA", "RIAN", "BAYU", "INDRA", "ADI", "ARIS", "DEDDY", "DIAN",
    "FAJAR", "GILANG", "HADI", "ILHAM", "KURNIA", "LUKMAN", "MAULANA", "NUR",
    "OKTO", "PANJI", "REZA", "SETIAWAN", "TAUFIK", "USMAN", "VICKY", "WIDODO",
    "YOGI", "BUDIMAN", "DARMAWAN", "GUNAWAN", "HERMAWAN", "ISMAIL", "IRFAN", "PRASETYO"
]

ID_THEMES = [
    "BERKAH", "BAROKAH", "AMANAH", "RIDHO", "IKHLAS", "REJEKI", "HOKI",
    "SUKSES", "JAYA", "MAJU", "LANCAR", "SENTOSA", "SEJAHTERA", "LESTARI",
    "ABADI", "SUBUR", "MAKMUR", "PRIMA", "MULIA", "AGUNG", "KENCANA"
]

ID_CITIES = [
    "JAKARTA", "SURABAYA", "BANDUNG", "MEDAN", "SEMARANG", "MAKASSAR",
    "PALEMBANG", "TANGERANG", "DEPOK", "BEKASI", "BOGOR", "BATAM",
    "PEKANBARU", "BANDAR LAMPUNG", "MALANG", "PADANG", "DENPASAR",
    "SAMARINDA", "BANJARMASIN", "SERANG", "YOGYAKARTA", "SOLO"
]

DEFAULT_BASE_GOBIZ_QRIS = "00020101021126610014COM.GO-JEK.WWW01189360000000000000000210G0000000000303UMI51440014ID.CO.QRIS.WWW0215ID10000000000000303UMI5204762953033605802ID5914TOKO CONTOH Q6007JAKARTA61051234562070703A016304B45D"

def crc16_ccitt(data: str) -> str:
    """Menghitung Checksum CRC16-CCITT standar EMVCo (Polinomial 0x1021, Init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data.encode("ascii", errors="replace"):
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def build_tlv(tag: str, val: str) -> str:
    """Membangun chunk Tag-Length-Value (TLV)."""
    val_bytes = val.encode("utf-8")
    length_str = f"{len(val_bytes):02d}"
    return f"{tag}{length_str}{val}"

def parse_emvco_payload(payload: str) -> Optional[List[Tuple[str, str]]]:
    """Mem-parsing string QRIS EMVCo menjadi daftar tuple (tag, value)."""
    clean = payload.strip()
    idx = clean.find("000201")
    if idx != -1:
        clean = clean[idx:]
    else:
        return None

    tlvs = []
    i = 0
    plen = len(clean)
    while i + 4 <= plen:
        tag = clean[i:i+2]
        try:
            length = int(clean[i+2:i+4])
        except ValueError:
            break
        val_start = i + 4
        val_end = val_start + length
        if val_end > plen:
            break
        val = clean[val_start:val_end]
        tlvs.append((tag, val))
        i = val_end
        if tag == "63":
            break
    return tlvs

def parse_sub_tlvs(tlv_str: str) -> List[Tuple[str, str]]:
    sub_tlvs = []
    i = 0
    l = len(tlv_str)
    while i + 4 <= l:
        stag = tlv_str[i:i+2]
        try:
            slen = int(tlv_str[i+2:i+4])
        except ValueError:
            break
        if i + 4 + slen > l:
            break
        sval = tlv_str[i+4:i+4+slen]
        sub_tlvs.append((stag, sval))
        i += 4 + slen
    return sub_tlvs

def rebuild_sub_tlvs(sub_tlvs: List[Tuple[str, str]]) -> str:
    return "".join(build_tlv(stag, sval) for stag, sval in sub_tlvs)

def get_random_merchant_name() -> str:
    pattern = random.randint(1, 3)
    if pattern == 1:
        raw = f"{random.choice(ID_PREFIXES)} {random.choice(ID_BUSINESS_NAMES)}"
    elif pattern == 2:
        raw = f"{random.choice(ID_PREFIXES)} {random.choice(ID_THEMES)}"
    else:
        raw = f"{random.choice(ID_BUSINESS_NAMES)} {random.choice(ID_THEMES)}"
    return raw[:25].upper()

def get_random_nmid() -> str:
    random_digits = ''.join(random.choices(string.digits, k=9))
    return f"ID2026{random_digits}"

def extract_token_from_input(raw_input: str) -> str:
    """
    Mengekstrak token JWT secara cerdas dari berbagai format input:
    - String token langsung: eyJ...
    - Format Bearer: Bearer eyJ...
    - Cookie access_token=eyJ... dari cURL GoFood Merchant Dashboard
    - Perintah cURL utuh dari browser DevTools (Network tab)
    """
    clean = raw_input.strip()
    if not clean:
        return ""

    # 1. Coba cari cookie access_token=eyJ... (Paling utama dari GoFood Merchant Dashboard)
    m_acc = re.search(r'access_token=([A-Za-z0-9_\-\.]+)', clean)
    if m_acc and m_acc.group(1).startswith("ey"):
        return m_acc.group(1).strip()

    # 2. Coba cari Authorization: Bearer eyJ... di dalam cURL / header
    m_bearer = re.search(r'Bearer\s+([A-Za-z0-9_\-\.]+)', clean, re.IGNORECASE)
    if m_bearer and m_bearer.group(1).startswith("ey"):
        return m_bearer.group(1).strip()

    # 3. Coba cari cookie sID=eyJ... jika dari web GoFood
    m_sid = re.search(r'sID=([A-Za-z0-9_\-\.]+)', clean)
    if m_sid and m_sid.group(1).startswith("ey"):
        return m_sid.group(1).strip()

    # 4. Coba cari cookie refresh_token=eyJ...
    m_ref = re.search(r'refresh_token=([A-Za-z0-9_\-\.]+)', clean)
    if m_ref and m_ref.group(1).startswith("ey"):
        return m_ref.group(1).strip()

    # 5. Coba cari token JWT langsung yang diawali eyJ...
    m_jwt = re.search(r'(eyJ[A-Za-z0-9_\-\.]+)', clean)
    if m_jwt:
        return m_jwt.group(1).strip()

    return clean.replace("Bearer ", "").strip()

def fetch_gobiz_merchant_info(auth_token: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Auto-Discovery Kredensial GoBiz dari 1 Token Bearer GoBiz / GoPay:
    Mengambil merchant_id, merchant_name, city, server_key Midtrans, pop_id / outlet_id,
    serta aspi_qr_string resmi langsung dari API resmi GoBiz (https://api.gobiz.co.id).
    Pengguna tidak perlu mencari Server Key atau Outlet ID secara manual!
    """
    clean_tok = extract_token_from_input(auth_token)

    if not clean_tok:
        return {"success": False, "error": "Token JWT kosong"}

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authentication-Type": "go-id",
        "Authorization": f"Bearer {clean_tok}",
        "Origin": "https://portal.gofoodmerchant.co.id",
        "Referer": "https://portal.gofoodmerchant.co.id/",
        "User-Agent": "Mozilla/5.0"
    }

    merchant_id = ""
    # Step 1: Dapatkan merchant_id dari /v1/users/me
    try:
        r = requests.get("https://api.gobiz.co.id/v1/users/me", headers=headers, timeout=timeout)
        if r.status_code == 200:
            merchant_id = r.json().get("user", {}).get("merchant_id", "")
    except Exception:
        pass

    # Fallback search payments jika /v1/users/me dibatasi
    if not merchant_id:
        try:
            r2 = requests.post("https://api.gobiz.co.id/v1/payments/search", headers=headers, json={"limit": 1}, timeout=timeout)
            if r2.status_code == 200:
                hits = r2.json().get("hits", [])
                if hits:
                    merchant_id = hits[0].get("transaction", {}).get("merchant_id", "")
        except Exception:
            pass

    if not merchant_id:
        return {"success": False, "error": "Gagal mendapatkan merchant_id. Pastikan token JWT masih aktif/belum expired."}

    # Step 2: Dapatkan detail outlet, Server Key Midtrans, Pop ID, dan Base QRIS
    try:
        r_mer = requests.get(f"https://api.gobiz.co.id/v1/merchants/{merchant_id}", headers=headers, timeout=timeout)
        if r_mer.status_code == 200:
            data = r_mer.json()
            pops = data.get("pops", [])
            pop_id = ""
            base_aspi_qris = ""
            if pops:
                pop_id = pops[0].get("pop_id", "")
                base_aspi_qris = pops[0].get("gopay", {}).get("aspi_qr_string", "")
            server_key = data.get("server_key", "")
            client_key = data.get("client_key", "")
            m_name = data.get("merchant_name") or data.get("vtweb_settings", {}).get("display_name", "")
            raw_city = data.get("outlet_city") or data.get("aspi", {}).get("merchant_city", "CILEGON")
            m_city = str(raw_city)[4:].strip() if str(raw_city).startswith("6007") else str(raw_city).strip()

            return {
                "success": True,
                "merchant_id": merchant_id,
                "merchant_name": m_name,
                "city": m_city,
                "server_key": server_key,
                "client_key": client_key,
                "pop_id": pop_id,
                "outlet_id": pop_id,
                "raw_qris": base_aspi_qris,
            }
        return {"success": False, "error": f"Gagal membaca data merchant (HTTP {r_mer.status_code})"}
    except Exception as e:
        return {"success": False, "error": f"Koneksi gagal: {e}"}

class GoBizQRISGenerator:
    """Generator QRIS GoBiz Dinamis Berdiri Sendiri (Standalone)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        gobiz_cfg = self.config.get("gobiz", {})
        self.mode = (gobiz_cfg.get("mode") or "api").lower().strip()
        self.raw_qris = gobiz_cfg.get("raw_qris") or DEFAULT_BASE_GOBIZ_QRIS
        self.server_key = gobiz_cfg.get("server_key", "").strip()
        self.outlet_id = gobiz_cfg.get("outlet_id", "").strip()
        self.pop_id = gobiz_cfg.get("pop_id", "").strip() or self.outlet_id
        self.merchant_name = gobiz_cfg.get("merchant_name", "").strip()
        self.city = gobiz_cfg.get("city", "").strip()
        self.auth_token = gobiz_cfg.get("auth_token", "").strip()
        self.auto_random = gobiz_cfg.get("auto_random_merchant", True)

    def create_dynamic_qris_midtrans_api(
        self,
        amount: int,
        order_id: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Membuat tagihan QRIS Dinamis resmi langsung via Midtrans Core API (GoBiz backend).
        Memerlukan Server Key Midtrans GoBiz & X-Pop-Id yang valid.
        """
        if not self.server_key:
            return False, "", {"error": "Server Key Midtrans GoBiz belum diatur di config.json."}

        target_order_id = order_id or f"GMA-{uuid.uuid4()}"
        auth_header = "Basic " + base64.b64encode(f"{self.server_key}:".encode()).decode()
        pop_target = self.pop_id or self.outlet_id

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "X-Pop-Id": pop_target
        }

        payload = {
            "payment_type": "qris",
            "transaction_details": {
                "order_id": target_order_id,
                "gross_amount": int(amount)
            },
            "qris": {
                "acquirer": "gopay"
            },
            "custom_field1": pop_target,
            "metadata": {
                "x-pop-id": pop_target,
                "tags": json.dumps({"service_type": "GOPAY_OFFLINE"})
            }
        }

        try:
            resp = requests.post(
                "https://api.midtrans.com/v2/charge",
                json=payload,
                headers=headers,
                timeout=10
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                qr_str = data.get("qr_string")
                if qr_str and "000201" in qr_str:
                    details = {
                        "amount": int(amount),
                        "order_id": target_order_id,
                        "transaction_id": data.get("transaction_id"),
                        "merchant_name": self.merchant_name or "GoBiz Merchant",
                        "city": self.city or "JAKARTA",
                        "mode": "API_MIDTRANS",
                        "expiry_time": data.get("expiry_time"),
                        "actions": data.get("actions", [])
                    }
                    return True, qr_str, details
            return False, "", {"error": f"Midtrans API HTTP {resp.status_code}: {resp.text[:120]}"}
        except Exception as e:
            return False, "", {"error": f"Midtrans API Error: {str(e)}"}

    def check_transaction_status(self, order_id: str) -> Dict[str, Any]:
        """
        Pengecekan status pembayaran transaksi Midtrans Core API secara real-time.
        Returns: {success, status: SETTLEMENT/PENDING, is_paid: bool, gross_amount, settlement_time}
        """
        if not self.server_key or not order_id:
            return {"success": False, "status": "UNKNOWN", "is_paid": False}

        auth_header = "Basic " + base64.b64encode(f"{self.server_key}:".encode()).decode()
        headers = {
            "Accept": "application/json",
            "Authorization": auth_header
        }
        status_url = f"https://api.midtrans.com/v2/{order_id}/status"
        try:
            resp = requests.get(status_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                st = str(data.get("transaction_status") or "").lower()
                is_paid = st in ("settlement", "success", "capture")
                return {
                    "success": True,
                    "status": st.upper(),
                    "is_paid": is_paid,
                    "order_id": order_id,
                    "gross_amount": data.get("gross_amount"),
                    "settlement_time": data.get("settlement_time"),
                    "source": "midtrans_api"
                }
            return {"success": False, "status": f"HTTP_{resp.status_code}", "is_paid": False}
        except Exception as e:
            return {"success": False, "status": "ERROR", "error": str(e), "is_paid": False}

    def modify_emvco_merchant(
        self,
        raw_qr: str,
        custom_name: Optional[str] = None,
        custom_city: Optional[str] = None,
        randomize_nmid: bool = True
    ) -> str:
        """
        Memodifikasi Tag 59 (Nama Toko), Tag 60 (Kota), dan Tag 51 (NMID) pada string QRIS
        sambil menjaga Tag 26 (PAN GoPay) & Tag 62 (Invoice) 100% UTUH.
        """
        tlvs = parse_emvco_payload(raw_qr)
        if not tlvs:
            return raw_qr

        m_name = (custom_name or get_random_merchant_name())[:25].upper()
        m_city = (custom_city or random.choice(ID_CITIES))[:15].upper()
        m_nmid = get_random_nmid() if randomize_nmid else None

        rebuilt = []
        for tag, val in tlvs:
            if tag == "63":
                continue
            elif tag == "59":
                rebuilt.append(build_tlv("59", m_name))
            elif tag == "60":
                rebuilt.append(build_tlv("60", m_city))
            elif tag == "51" and m_nmid:
                sub_tlvs = parse_sub_tlvs(val)
                new_subs = []
                for stag, sval in sub_tlvs:
                    if stag == "02":
                        new_subs.append(("02", m_nmid))
                    else:
                        new_subs.append((stag, sval))
                rebuilt.append(build_tlv("51", rebuild_sub_tlvs(new_subs)))
            else:
                rebuilt.append(build_tlv(tag, val))

        before_crc = "".join(rebuilt) + "6304"
        return f"{before_crc}{crc16_ccitt(before_crc)}"

    def create_dynamic_qris_standalone(
        self,
        amount: int,
        custom_name: Optional[str] = None,
        custom_city: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Membuat QRIS dinamis mandiri secara lokal (Offline / Standalone).
        Injeksi nominal Tag 54 dan Tag 62 langsung ke base QRIS merchant.
        """
        if amount <= 0:
            return False, "", {"error": "Nominal harus lebih dari 0"}

        tlvs = parse_emvco_payload(self.raw_qris)
        if not tlvs:
            return False, "", {"error": "Base QRIS tidak valid"}

        m_name = (custom_name or self.merchant_name or get_random_merchant_name())[:25].upper()
        m_city = (custom_city or self.city or random.choice(ID_CITIES))[:15].upper()
        m_nmid = get_random_nmid()
        amount_str = str(int(amount))

        rebuilt_parts = []
        has_tag_54 = False
        has_tag_62 = False

        for tag, val in tlvs:
            if tag == "63":
                continue
            elif tag == "01":
                # QRIS Dinamis mutlak Tag 01 = "12"
                rebuilt_parts.append(build_tlv("01", "12"))
            elif tag == "26":
                # Tag 26 (PAN GoPay Merchant) MUTLAK TETAP ASLI!
                rebuilt_parts.append(build_tlv("26", val))
            elif tag == "51":
                # Acak Subtag 02 (NMID)
                sub_tlvs = parse_sub_tlvs(val)
                new_subs = []
                for stag, sval in sub_tlvs:
                    if stag == "02":
                        new_subs.append(("02", m_nmid))
                    else:
                        new_subs.append((stag, sval))
                rebuilt_parts.append(build_tlv("51", rebuild_sub_tlvs(new_subs)))
            elif tag == "54":
                rebuilt_parts.append(build_tlv("54", amount_str))
                has_tag_54 = True
            elif tag == "59":
                rebuilt_parts.append(build_tlv("59", m_name))
            elif tag == "60":
                rebuilt_parts.append(build_tlv("60", m_city))
            elif tag == "62":
                # Generate Subtag 50 (Invoice) + Subtag 07 (Terminal)
                now_ts = time.strftime("%Y%m%d%H%M%S")
                rnd_alnum = "".join(random.choices(string.ascii_letters + string.digits, k=12))
                order_ref = f"A2{now_ts}{rnd_alnum}"
                sub50 = build_tlv("50", order_ref)
                sub07 = build_tlv("07", "A01")
                rebuilt_parts.append(build_tlv("62", sub50 + sub07))
                has_tag_62 = True
            else:
                rebuilt_parts.append(build_tlv(tag, val))

        if not has_tag_54:
            new_parts = []
            inserted = False
            for p in rebuilt_parts:
                tcode = p[:2]
                if tcode in ("58", "59") and not inserted:
                    new_parts.append(build_tlv("54", amount_str))
                    inserted = True
                new_parts.append(p)
            if not inserted:
                new_parts.append(build_tlv("54", amount_str))
            rebuilt_parts = new_parts

        if not has_tag_62:
            now_ts = time.strftime("%Y%m%d%H%M%S")
            rnd_alnum = "".join(random.choices(string.ascii_letters + string.digits, k=12))
            order_ref = f"A2{now_ts}{rnd_alnum}"
            sub50 = build_tlv("50", order_ref)
            sub07 = build_tlv("07", "A01")
            rebuilt_parts.append(build_tlv("62", sub50 + sub07))

        payload_before_crc = "".join(rebuilt_parts) + "6304"
        crc = crc16_ccitt(payload_before_crc)
        final_qr = f"{payload_before_crc}{crc}"

        details = {
            "amount": amount,
            "merchant_name": m_name,
            "city": m_city,
            "nmid": m_nmid,
            "crc": crc,
            "mode": "STANDALONE_LOCAL"
        }
        return True, final_qr, details

    def generate_qris_string(
        self,
        amount: int,
        custom_name: Optional[str] = None,
        custom_city: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Pintu gerbang pembuatan QRIS dinamis (Dual-Engine):
        1. Jika mode 'api' dan Server Key Midtrans tersedia: panggil Midtrans Core API resmi!
        2. Jika mode 'standalone' atau Midtrans API gagal: fallback otomatis ke Standalone ASPI lokal.
        """
        if self.mode == "api" and self.server_key:
            ok, qr_api, det_api = self.create_dynamic_qris_midtrans_api(amount)
            if ok:
                final_qr = qr_api
                if self.auto_random:
                    final_qr = self.modify_emvco_merchant(
                        qr_api,
                        custom_name=custom_name,
                        custom_city=custom_city,
                        randomize_nmid=True
                    )
                    det_api["merchant_name"] = "MODIFIED_RANDOM"
                return True, final_qr, det_api
            print(f"[!] Midtrans API gagal: {det_api.get('error')}. Beralih ke Standalone ASPI...")

        return self.create_dynamic_qris_standalone(amount, custom_name, custom_city)

    def save_qr_image(self, qr_string: str, output_path: str, scale: int = 2) -> bool:
        """
        Merender string QRIS menjadi format kartu modern sesuai Gambar 3:
        - Kartu putih elegan dengan sudut rounded (rounded rectangle).
        - Tepian / margin putih luas (quiet zone lega, tidak mepen ke tepi).
        - Frame background gelap (#0F1729) berbingkai presisi sehingga kontras maksimal.
        - Memastikan 100% terbaca mulus oleh scanner Bitget Wallet / e-wallet.
        """
        if not HAS_QRCODE:
            print("[!] Library 'qrcode' atau 'PIL' belum terinstall.")
            return False

        try:
            from PIL import ImageDraw

            # Proporsi presisi identik Gambar 3 (Base: 315x270, QR 223x223)
            img_w = 315 * scale
            img_h = 270 * scale
            qr_target_size = 223 * scale
            corner_radius = 12 * scale
            bg_color = (15, 23, 41, 255)       # Dark navy #0F1729
            card_color = (255, 255, 255, 255)  # Putih murni

            pad_x = 4 * scale
            pad_y = 3 * scale

            # 1. Generate QR code dengan border 0 (karena margin dikontrol penuh oleh kartu putih)
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=0,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            raw_qr = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

            # Resampling NEAREST agar modul hitam QR tajam tanpa blur
            raw_qr = raw_qr.resize((qr_target_size, qr_target_size), Image.Resampling.NEAREST)

            # 2. Buat kanvas background berbingkai gelap
            canvas = Image.new("RGBA", (img_w, img_h), bg_color)
            draw = ImageDraw.Draw(canvas)

            # 3. Gambar kartu putih dengan sudut membulat (rounded rectangle)
            card_box = [pad_x, pad_y, img_w - pad_x, img_h - pad_y]
            draw.rounded_rectangle(card_box, radius=corner_radius, fill=card_color)

            # 4. Tempel QR code tepat di tengah kartu putih (tepian lega & simetris)
            qr_x = (img_w - qr_target_size) // 2
            qr_y = (img_h - qr_target_size) // 2
            canvas.paste(raw_qr, (qr_x, qr_y))

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            canvas.save(output_path, format="PNG")
            return True
        except Exception as e:
            print(f"[!] Gagal membuat file gambar QR: {e}")
            return False

    def create_and_save_qris(self, amount: int, output_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Satu langkah mudah: buat string QRIS dinamis dan simpan ke file gambar PNG."""
        success, qr_str, details = self.generate_qris_string(amount)
        if not success:
            return False, "", details

        saved = self.save_qr_image(qr_str, output_path)
        if not saved:
            return False, qr_str, {"error": "Gagal merender gambar QR"}

        details["image_path"] = output_path
        return True, qr_str, details
