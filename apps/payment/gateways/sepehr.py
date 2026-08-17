import json
import requests
from django.conf import settings
from django.urls import reverse
from .base import BasePaymentGateway, PaymentGatewayError


class SepehrGateway(BasePaymentGateway):
    """
    اتصال به درگاه پرداخت الکترونیک سپهر (بانک صادرات) - روش توکن.
    مرجع: «راهنمای راه‌اندازی درگاه پرداخت اینترنتی پرداخت الکترونیک سپهر (توکن)» Ver 3.0.0

    جریان کار:
      1) GetToken -> دریافت AccessToken (معادل authority در بقیه‌ی درگاه‌ها)
      2) هدایت کاربر با POST خودکار (فرم مخفی) به https://sepehr.shaparak.ir:8080/Pay
      3) سپهر نتیجه را با POST به callbackURL برمی‌گرداند (بدون توکن! تطبیق بر اساس invoiceID)
      4) Advice   -> تایید نهایی/تسویه‌ی تراکنش نزد سپهر (معادل verify_payment اینجا)
         نیازمند «رسید دیجیتال» (digitalreceipt) که فقط در همان callback مرحله‌ی ۳ ارسال می‌شود؛
         بنابراین باید پیش از فراخوانی verify_payment در payment.extra_data ذخیره شده باشد
         (این کار در SepehrCallbackAPIView/serializers.py انجام می‌شود).
    """

    GET_TOKEN_URL = "https://sepehr.shaparak.ir:8081/V1/PeymentApi/GetToken"
    ADVICE_URL = "https://sepehr.shaparak.ir:8081/V1/PeymentApi/Advice"
    REDIRECT_URL = "https://sepehr.shaparak.ir:8080/Pay"

    # سرویس بازگشت وجه فقط با درخواست کتبی به واحد عملیات سپهر فعال می‌شود:
    # ROLLBACK_URL = "https://sepehr.shaparak.ir:8081/V1/PeymentApi/Rollback"

    def _post(self, url, payload):
        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PaymentGatewayError(f"خطا در ارتباط با درگاه سپهر: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise PaymentGatewayError("پاسخ نامعتبر از درگاه سپهر دریافت شد.") from exc

    @staticmethod
    def _rial_amount(payment) -> int:
        return int(payment.amount) * 10

    def _redirect_view_url(self, payment) -> str:
        path = reverse("payment-gateway-redirect", args=["sepehr", payment.id])
        return f"{settings.BACKEND_BASE_URL.rstrip('/')}{path}"

    def create_payment(self, payment):
        terminal_id = settings.SEPEHR_TERMINAL_ID

        payload = {
            "Amount": self._rial_amount(payment),
            "callbackURL": settings.SEPEHR_CALLBACK_URL,
            # چون در callback سپهر توکن/authority برگردانده نمی‌شود، شماره سفارش
            # را به‌عنوان invoiceID می‌فرستیم تا بتوانیم پرداخت را در callback پیدا کنیم.
            "invoiceID": payment.order.order_number,
            "terminalID": terminal_id,
            "payload": json.dumps({"payment_id": str(payment.id)}, ensure_ascii=False),
        }
        data = self._post(self.GET_TOKEN_URL, payload)

        if str(data.get("Status")) != "0":
            raise PaymentGatewayError(data.get("Message") or "خطا در دریافت توکن از سپهر.")

        token = data.get("AccessToken") or data.get("Accesstoken")

        if not token:
            raise PaymentGatewayError("درگاه سپهر پاسخ موفق برگرداند اما توکن پرداخت در پاسخ وجود ندارد.")

        return {"authority": token, "payment_url": self._redirect_view_url(payment)}

    def build_redirect_form(self, payment):
        """
        فیلدهای لازم برای فرم auto-submit به صفحه‌ی پرداخت سپهر.
        توسط GatewayRedirectView استفاده می‌شود.
        """
        fields = {
            "TerminalID": settings.SEPEHR_TERMINAL_ID,
            "token": payment.authority,
            "getMethod": "0",  # 0 = برگشت نتیجه با POST (پیش‌فرض مستند)
        }
        return self.REDIRECT_URL, fields

    def verify_payment(self, payment):
        extra = payment.extra_data or {}
        digital_receipt = extra.get("digitalreceipt")

        if not digital_receipt:
            raise PaymentGatewayError("رسید دیجیتال تراکنش سپهر موجود نیست؛ ابتدا باید callback سپهر پردازش شده باشد.")

        payload = {
            "digitalreceipt": digital_receipt,
            "Tid": settings.SEPEHR_TERMINAL_ID,
        }
        data = self._post(self.ADVICE_URL, payload)

        gateway_status_raw = str(data.get("Status") or "").strip()
        gateway_status = gateway_status_raw.upper()

        # سپهر ممکن است Status را با بزرگی/کوچکی متفاوت حروف برگرداند.
        # OK و Duplicate هر دو به معنی تایید موفق تراکنش هستند.
        success = gateway_status in ("OK", "DUPLICATE")

        message = data.get("Message", "")

        if success:
            # طبق نکات امنیتی مستند: در صورت موفقیت، ReturnId برابر مبلغ واقعی تراکنش است
            # و باید با مبلغ فاکتور مقایسه شود.
            expected_amount = self._rial_amount(payment)
            try:
                returned_amount = int(data.get("ReturnId") or 0)
            except (TypeError, ValueError):
                returned_amount = 0
            if returned_amount != expected_amount:
                success = False
                message = "مبلغ تایید شده توسط سپهر با مبلغ فاکتور مطابقت ندارد."

        return {
            "success": success,
            "code": gateway_status_raw,
            "ref_id": extra.get("rrn") or extra.get("tracenumber"),
            "card_pan": extra.get("cardnumber", ""),
            "message": message,
        }
