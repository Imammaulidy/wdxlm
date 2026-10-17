"""
Multi-IMAP Email OTP Module
---------------------------
Modul untuk membaca kode OTP dari email Bitget via Multi-IMAP (Gmail, Outlook, Rambler, Firstmail, dll).
Diadaptasi dari COINS_PAYMENT_GATEWAY engine.
"""

import sys
import imaplib
import email
from email.header import decode_header
import re
import time
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger("EmailOTP")

def decode_mime_header(header_value: Optional[str]) -> str:
    """Decode encoded MIME header (seperti =?UTF-8?B?...?=) menjadi plain string"""
    if not header_value:
        return ""
    try:
        decoded_fragments = decode_header(header_value)
        result = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                if encoding:
                    try:
                        result.append(text.decode(encoding, errors="replace"))
                    except Exception:
                        result.append(text.decode("utf-8", errors="replace"))
                else:
                    result.append(text.decode("utf-8", errors="replace"))
            else:
                result.append(str(text))
        return "".join(result)
    except Exception:
        return str(header_value)

class EmailOTPReader:
    def __init__(self, email_addr: str, password: str, imap_server: Optional[str] = None, imap_port: int = 993, use_ssl: bool = True):
        self.email_addr = email_addr.strip()
        self.password = password.replace(" ", "").strip()
        
        # Auto detect server IMAP dari domain jika tidak dispesifikasikan
        if not imap_server or imap_server == "imap.gmail.com":
            domain = self.email_addr.split("@")[-1].lower() if "@" in self.email_addr else ""
            if "icloud" in domain or "me.com" in domain or "mac.com" in domain:
                self.imap_server = "imap.mail.me.com"
            elif "outlook" in domain or "hotmail" in domain or "live" in domain:
                self.imap_server = "outlook.office365.com"
            elif "rambler" in domain or "myrambler" in domain:
                self.imap_server = "imap.rambler.ru"
            elif "firstmail" in domain or "fmail" in domain:
                self.imap_server = "imap.firstmail.ltd"
            elif "yahoo" in domain:
                self.imap_server = "imap.mail.yahoo.com"
            else:
                self.imap_server = imap_server or "imap.gmail.com"
        else:
            self.imap_server = imap_server

        self.imap_port = int(imap_port)
        self.use_ssl = use_ssl

    def is_configured(self) -> bool:
        return bool(
            self.email_addr
            and self.password
            and "ISIKAN" not in self.email_addr.upper()
            and "ISIKAN" not in self.password.upper()
        )

    def test_connection(self) -> Dict[str, Any]:
        """Uji coba login ke server IMAP"""
        if not self.is_configured():
            return {"success": False, "error": "Email/password belum diisi secara valid."}
        try:
            if self.use_ssl:
                mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                mail = imaplib.IMAP4(self.imap_server, self.imap_port)
            mail.login(self.email_addr, self.password)
            mail.select("INBOX", readonly=True)
            mail.logout()
            return {"success": True, "message": f"Login IMAP Berhasil: {self.email_addr}"}
        except Exception as e:
            return {"success": False, "error": f"Login IMAP Gagal: {e}"}

    def get_latest_otp(self, search_query: str = "bitget", min_timestamp: float = 0, timeout: int = 300) -> Dict[str, Any]:
        """
        Real-Time IMAP Watcher:
        Connecting ke IMAP, polling inbox tanpa henti sampai email OTP (Bitget / Apple / iCloud) TERBARU masuk.
        Hanya menerima email yang masuk SETELAH 'min_timestamp' (saat tombol Minta OTP diklik).
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Email OTP belum dikonfigurasi secara valid."
            }

        start_time = time.time()
        print(f"[*] [IMAP WATCHER] Menghubungkan ke {self.imap_server}:{self.imap_port} ({self.email_addr})...")
        
        last_log_sec = -1

        while (time.time() - start_time) < timeout:
            elapsed_sec = int(time.time() - start_time)
            if elapsed_sec != last_log_sec:
                last_log_sec = elapsed_sec
                sys.stdout.write(f"\r[*] [IMAP WATCHER] Menunggu email OTP terbaru masuk ({elapsed_sec:02d}s)...   ")
                sys.stdout.flush()

            try:
                if self.use_ssl:
                    mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
                else:
                    mail = imaplib.IMAP4(self.imap_server, self.imap_port)
                    
                mail.login(self.email_addr, self.password)
                mail.select("INBOX", readonly=True)

                status, messages = mail.search(None, 'ALL')
                if status != "OK" or not messages[0]:
                    status, messages = mail.search(None, f'OR FROM "{search_query}" SUBJECT "{search_query}"')

                if status == "OK" and messages[0]:
                    nums = [int(n) for n in messages[0].split()]
                    if nums:
                        latest_ids = sorted(nums, reverse=True)[:5]
                        for latest_id in latest_ids:
                            status, msg_data = mail.fetch(str(latest_id), "(RFC822)")
                            if status == "OK" and msg_data and msg_data[0]:
                                raw_email = msg_data[0][1]
                                msg = email.message_from_bytes(raw_email)
                                
                                # Cek tanggal email (Mencari email yang masuk setelah request OTP)
                                msg_date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                                msg_timestamp = 0
                                if msg_date_tuple:
                                    msg_timestamp = email.utils.mktime_tz(msg_date_tuple)
                                
                                # Jika min_timestamp disetel, abaikan email yang terbit sebelum request OTP
                                if min_timestamp > 0 and msg_timestamp > 0:
                                    if msg_timestamp < (min_timestamp - 15):
                                        continue

                                subject = decode_mime_header(msg.get("Subject"))
                                body = self._get_email_body(msg)

                                full_text = f"{subject}\n{body}"
                                otp_code = self._extract_otp(full_text)

                                if otp_code:
                                    try:
                                        mail.logout()
                                    except Exception:
                                        pass
                                    sys.stdout.write("\n")
                                    sys.stdout.flush()
                                    return {
                                        "success": True,
                                        "otp": otp_code,
                                        "inbox": self.email_addr,
                                        "subject": subject,
                                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                                        "elapsed": round(time.time() - start_time, 1)
                                    }
                try:
                    mail.logout()
                except Exception:
                    pass

            except Exception as e:
                pass

            time.sleep(1.0)

        sys.stdout.write("\n")
        sys.stdout.flush()
        return {
            "success": False,
            "error": f"Timeout {timeout}s: OTP tidak ditemukan di {self.email_addr}"
        }

    def _get_email_body(self, msg) -> str:
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if "attachment" in content_disposition:
                    continue
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="replace") + " "
                    except Exception:
                        pass
                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        html = payload.decode(charset, errors="replace")
                        clean_text = re.sub(r'<style[^>]*>[\s\S]*?</style>', ' ', html, flags=re.IGNORECASE)
                        clean_text = re.sub(r'<script[^>]*>[\s\S]*?</script>', ' ', clean_text, flags=re.IGNORECASE)
                        clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                        body += clean_text + " "
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                raw = payload.decode(charset, errors="replace")
                if "<html" in raw.lower() or "<div" in raw.lower():
                    clean_text = re.sub(r'<style[^>]*>[\s\S]*?</style>', ' ', raw, flags=re.IGNORECASE)
                    clean_text = re.sub(r'<script[^>]*>[\s\S]*?</script>', ' ', clean_text, flags=re.IGNORECASE)
                    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
                    body = clean_text
                else:
                    body = raw
            except Exception:
                pass

        return re.sub(r'\s+', ' ', body).strip()

    def _extract_otp(self, text: str) -> Optional[str]:
        if not text:
            return None

        # Prioritas 1: OTP Apple / iCloud / Apple ID
        apple_patterns = [
            r'(?:Apple\s*ID|Apple|iCloud|Verify\s*email)[^\d]{0,80}(\d{6})\b',
            r'\b(\d{6})\b[^\d]{0,80}(?:Apple|iCloud)',
            r'Enter\s*the\s*verification\s*code[^\d]{0,80}(\d{6})\b',
            r'kode\s*verifikasi[^\d]{0,60}(\d{6})\b',
        ]
        for pattern in apple_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        # Prioritas 2: OTP di dekat kata 'Verification Code', 'OTP', 'Code', 'Verifikasi', 'Security Code'
        priority_patterns = [
            r'(?:Verification\s*Code|VerificationCode|Kode\s*Verifikasi|Security\s*Code|Verifikasi)[^\d]{0,40}(\d{6})\b',
            r'\b(\d{6})\b[^\d]{0,40}(?:is\s*your\s*verification|adalah\s*kode\s*verifikasi)',
            r'(?:OTP|code|kode|sandi)[^\d]{0,20}(\d{6})\b',
        ]

        for pattern in priority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        # Prioritas 3: Cari semua 6-digit number yang bukan deretan angka berulang
        all_six_digits = re.findall(r'\b\d{6}\b', text)
        if all_six_digits:
            for digit in all_six_digits:
                if not all(c == digit[0] for c in digit):
                    return digit

        return None


def fetch_bitget_otp(email_user: str, email_pass: str, imap_server: str = "imap.gmail.com", imap_port: int = 993, use_ssl: bool = True, min_timestamp: float = 0, timeout: int = 300):
    reader = EmailOTPReader(email_user, email_pass, imap_server=imap_server, imap_port=imap_port, use_ssl=use_ssl)
    res = reader.get_latest_otp(min_timestamp=min_timestamp, timeout=timeout)
    if res.get("success"):
        return res.get("otp")
    return None
