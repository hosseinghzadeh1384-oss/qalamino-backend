from abc import ABC, abstractmethod


class PaymentGatewayError(Exception):
    """خطای عمومی هنگام ارتباط یا دریافت پاسخ نامعتبر از یک درگاه پرداخت."""


class BasePaymentGateway(ABC):
    @abstractmethod
    def create_payment(self, payment):
        """درخواست ایجاد تراکنش را به درگاه می‌فرستد و {authority, payment_url} برمی‌گرداند.

        برای درگاه‌هایی که کاربر باید مستقیماً با GET به یک لینک هدایت شود،
        payment_url همان لینک نهایی درگاه است.
        برای درگاه‌هایی که نیازمند POST خودکار با چند فیلد هستند (سیزپی/سپهر)،
        payment_url به یک صفحه‌ی واسط داخلی (GatewayRedirectView) اشاره می‌کند که
        از متد اختیاری ``build_redirect_form`` همین کلاس استفاده می‌کند.
        """

    @abstractmethod
    def verify_payment(self, payment):
        """تراکنش را نزد درگاه verify/تایید می‌کند و
        {success, code, ref_id, card_pan, message} برمی‌گرداند."""

    # اختیاری - فقط توسط درگاه‌هایی که برای هدایت کاربر نیاز به POST چند فیلدی
    # دارند پیاده‌سازی می‌شود (امضای پیشنهادی):

    def build_redirect_form(self, payment) -> tuple[str, dict]:
        """(action_url, fields) برای فرم auto-submit صفحه‌ی واسط را برمی‌گرداند."""
