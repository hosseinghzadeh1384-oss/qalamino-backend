import json
import jdatetime
import requests
from django.conf import settings
from django.urls import reverse
from .base import BasePaymentGateway, PaymentGatewayError
from .sizpay_crypto import SizPaySigner


class SizPayGateway(BasePaymentGateway):
    """
    اتصال به درگاه پرداخت سیزپی (SizPay) با متد REST.
    مرجع: «راهنمای نحوه اتصال به درگاه پرداخت اینترنتی – سیزپی» نسخه‌ی V_1.012.030531

    جریان کار:
      1) GetToken  -> دریافت Token یک‌بارمصرف (معادل authority در بقیه‌ی درگاه‌ها)
      2) هدایت کاربر با POST خودکار (فرم مخفی) به صفحه‌ی پرداخت سیزپی
      3) سیزپی نتیجه را با POST به ReturnURL برمی‌گرداند (کد سیزپی: Token را هم برمی‌گرداند)
      4) Confirm    -> تایید نهایی تراکنش نزد سیزپی (معادل verify_payment اینجا)
    """

    GET_TOKEN_URL = "https://rt.sizpay.ir/api/Payment/GetToken"
    CONFIRM_URL = "https://rt.sizpay.ir/api/Payment/Confirm"
    REDIRECT_URL = "https://rt.sizpay.ir/Route/Payment"
    # عملیات بازگشت وجه (Reverse) عمداً پیاده‌سازی نشده و در صورت نیاز باید
    # به‌صورت مجزا (مثلاً از پنل ادمین) روی همین الگو اضافه شود:
    # REVERSE_URL = "https://rt.sizpay.ir/api/Payment/Reverse"

    SUCCESS_CODES = ("0", "00")

    def __init__(self):
        self._signer = SizPaySigner(
            aes_key_b64=settings.SIZPAY_KEY,
            aes_iv_b64=settings.SIZPAY_IV,
            sign_key=settings.SIZPAY_SIGN_KEY,
        )

    # ------------------------------------------------------------------
    # کمکی‌ها
    # ------------------------------------------------------------------

    def _post(self, url, payload):
        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PaymentGatewayError(f"خطا در ارتباط با درگاه سیزپی: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise PaymentGatewayError("پاسخ نامعتبر از درگاه سیزپی دریافت شد.") from exc

    @staticmethod
    def _rial_amount(payment) -> int:
        # مبلغ در پروژه به تومان ذخیره می‌شود؛ سیزپی مبلغ را به ریال می‌خواهد.
        return int(payment.amount) * 10

    @staticmethod
    def _numeric_invoice_no(payment) -> str:
        # InvoiceNo سیزپی باید کاملاً عددی و حداکثر ۵۰ کاراکتر باشد؛ چون شماره
        # سفارش ما فرمت الفبایی دارد (GLM-xxxxxxxxxx)، یک رشته‌ی عددی یکتا از
        # UUID پرداخت ساخته می‌شود.
        return str(payment.id.int)[:18]

    def _redirect_view_url(self, payment) -> str:
        path = reverse("payment-gateway-redirect", args=["sizpay", payment.id])
        return f"{settings.BACKEND_BASE_URL.rstrip('/')}{path}"

    # ------------------------------------------------------------------
    # API عمومی BasePaymentGateway
    # ------------------------------------------------------------------

    def create_payment(self, payment):
        merchant_id = settings.SIZPAY_MERCHANT_ID
        terminal_id = settings.SIZPAY_TERMINAL_ID
        amount = self._rial_amount(payment)
        doc_date = jdatetime.date.today().strftime("%Y/%m/%d")
        order_id = payment.order.order_number
        return_url = settings.SIZPAY_CALLBACK_URL
        extra_inf = ""
        invoice_no = self._numeric_invoice_no(payment)
        # ترتیب فیلدها دقیقاً باید مطابق مستند باشد: P1..P8
        sign_data = self._signer.build_sign_data(
            [merchant_id, terminal_id, amount, doc_date, order_id, return_url, extra_inf, invoice_no]
        )
        payer_mobile = getattr(payment.user, "phone_number", "") or ""
        app_extra_inf = {
            "PayerNm": "",
            "PayerMobile": payer_mobile,
            "PayerEmail": "",
            "Descr": payment.description or "",
            "PayerIP": "",
            "PayTitle": payment.description or "",
            "PayerNCode": "",
        }

        payload = {
            "MerchantID": merchant_id,
            "TerminalID": terminal_id,
            "Amount": amount,
            "DocDate": doc_date,
            "OrderID": order_id,
            "ReturnURL": return_url,
            "ExtraInf": extra_inf,
            "InvoiceNo": invoice_no,
            "AppExtraInf": json.dumps(app_extra_inf, ensure_ascii=False),
            "SignData": sign_data,
        }

        data = self._post(self.GET_TOKEN_URL, payload)

        if str(data.get("ResCod")) not in self.SUCCESS_CODES:
            raise PaymentGatewayError(data.get("Message") or "خطا در دریافت توکن از سیزپی.")

        token = data["Token"]

        return {"authority": token, "payment_url": self._redirect_view_url(payment)}

    def build_redirect_form(self, payment):
        """
        فیلدهای لازم برای فرم auto-submit به صفحه‌ی پرداخت سیزپی.
        توسط GatewayRedirectView استفاده می‌شود.
        """
        merchant_id = settings.SIZPAY_MERCHANT_ID
        terminal_id = settings.SIZPAY_TERMINAL_ID
        token = payment.authority
        sign_data = self._signer.build_sign_data([merchant_id, terminal_id, token])

        fields = {
            "MerchantID": merchant_id,
            "TerminalID": terminal_id,
            "Token": token,
            "SignData": sign_data,
        }
        return self.REDIRECT_URL, fields

    def verify_payment(self, payment):
        merchant_id = settings.SIZPAY_MERCHANT_ID
        terminal_id = settings.SIZPAY_TERMINAL_ID
        token = payment.authority

        sign_data = self._signer.build_sign_data([merchant_id, terminal_id, token])

        payload = {
            "MerchantID": merchant_id,
            "TerminalID": terminal_id,
            "Token": token,
            "SignData": sign_data,
        }
        data = self._post(self.CONFIRM_URL, payload)

        success = str(data.get("ResCod")) in self.SUCCESS_CODES
        message = data.get("Message", "")

        if success:
            # طبق نکات امنیتی مستند: مبلغ تایید شده باید با مبلغ فاکتور مطابقت داشته باشد
            expected_amount = self._rial_amount(payment)
            try:
                returned_amount = int(data.get("Amount") or 0)
            except (TypeError, ValueError):
                returned_amount = 0
            if returned_amount != expected_amount:
                success = False
                message = "مبلغ تایید شده توسط سیزپی با مبلغ فاکتور مطابقت ندارد."

        return {
            "success": success,
            "code": data.get("ResCod"),
            "ref_id": data.get("RefNo") or data.get("TraceNo"),
            "card_pan": data.get("CardNo", ""),
            "message": message,
        }
