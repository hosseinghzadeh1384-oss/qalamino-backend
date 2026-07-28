"""
پیاده‌سازی الگوریتم امضا/رمزنگاری SignData سیزپی، طبق «راهنمای نحوه اتصال به
درگاه پرداخت اینترنتی – سیزپی (REST)»:

    1) S = پارامترها با کاراکتر کاما (,) از هم جدا می‌شوند (ترتیب حفظ می‌شود)
    2) H = HMAC-SHA256(S) با «کلید امضای الکترونیکی» (به‌صورت متن UTF-8،
           بر خلاف کلید AES این کلید Base64 نیست - طبق نمونه‌کد رسمی #C)
    3) F = S + "," + H
    4) SignData = Base64( AES-256-CBC-Encrypt(F) )  با کلید/IV رمزنگاری (Base64)

این پیاده‌سازی دقیقاً معادل نمونه‌کدهای #C و PHP موجود در مستند رسمی سیزپی است.
"""
import base64
import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class SizPaySigner:
    def __init__(self, aes_key_b64: str, aes_iv_b64: str, sign_key: str):
        if not aes_key_b64 or not aes_iv_b64 or not sign_key:
            raise ValueError("SIZPAY_KEY / SIZPAY_IV / SIZPAY_SIGN_KEY باید در تنظیمات پروژه مقداردهی شوند.")
        self._aes_key = base64.b64decode(aes_key_b64)
        self._aes_iv = base64.b64decode(aes_iv_b64)
        # طبق نمونه‌کد رسمی (HMACSHA256(varArrSHA2Key))، کلید امضا به‌صورت
        # رشته‌ی UTF-8 خام استفاده می‌شود، نه Base64-decoded.
        self._sign_key = sign_key.encode("utf-8")

    @staticmethod
    def _join(fields) -> str:
        return ",".join("" if f is None else str(f) for f in fields)

    def build_sign_data(self, fields) -> str:
        """فیلدها را طبق ترتیب مستند رشته می‌کند و SignData نهایی را برمی‌گرداند."""
        s = self._join(fields)
        h_bytes = hmac.new(self._sign_key, s.encode("utf-8"), hashlib.sha256).digest()
        h = base64.b64encode(h_bytes).decode("utf-8")
        f = f"{s},{h}"

        cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_iv)
        encrypted = cipher.encrypt(pad(f.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        """در صورت نیاز به بازکردن یک SignData (مثلاً برای دیباگ)."""
        cipher = AES.new(self._aes_key, AES.MODE_CBC, self._aes_iv)
        raw = base64.b64decode(encrypted_b64)
        decrypted = unpad(cipher.decrypt(raw), AES.block_size)
        return decrypted.decode("utf-8")
