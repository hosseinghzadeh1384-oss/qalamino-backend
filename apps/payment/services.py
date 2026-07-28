from django.db import transaction
from django.utils import timezone
from apps.orders.models import Order
from .gateways.base import PaymentGatewayError
from .gateways.factory import PaymentGatewayFactory
from .models import Payment, PaymentStatus


class PaymentServiceError(Exception):
    """خطای قابل‌نمایش به کاربر، هنگام شکست ایجاد/تایید پرداخت."""


class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_payment_request(payment):
        gateway = PaymentGatewayFactory.get_gateway(payment.gateway)
        try:
            result = gateway.create_payment(payment)
        except PaymentGatewayError as exc:
            # تراکنش pending بدون authority باقی می‌ماند تا آماری از تلاش‌های ناموفق داشته باشیم؛
            # کاربر پیام خطا می‌بیند و می‌تواند دوباره تلاش کند.
            payment.mark_as_failed()
            raise PaymentServiceError(str(exc)) from exc

        payment.authority = result["authority"]
        payment.payment_url = result["payment_url"]
        payment.save(update_fields=["authority", "payment_url", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def mark_failed(payment):
        """برای مواردی که خود درگاه پرداخت را ناموفق اعلام کرده (status=NOK) و اصلاً نیازی به verify نیست."""
        order = Order.objects.select_for_update().get(pk=payment.order_id)

        payment.mark_as_failed()
        if order.status == Order.Status.PENDING_PAYMENT:
            order.status = Order.Status.FAILED
            order.save(update_fields=["status", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def verify_payment(payment):
        # قفل کردن سفارش و خودِ پرداخت تا از race condition بین verify همزمان
        # (مثلاً کاربر + callback بانک، یا callback تکراری از سمت بانک) جلوگیری شود
        order = Order.objects.select_for_update().get(pk=payment.order_id)
        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        # idempotency: اگر این پرداخت قبلاً نهایی شده (موفق یا ناموفق)، دیگر دوباره
        # به درگاه بانک درخواست verify نمی‌زنیم. برخی درگاه‌ها (مثل سیزپی) روی
        # confirm تکراریِ یک تراکنش که قبلاً تایید شده، خطا برمی‌گردانند و بدون این
        # چک، پرداختِ واقعاً موفق به‌اشتباه FAILED می‌شد.
        if payment.status != PaymentStatus.PENDING:
            return payment

        gateway = PaymentGatewayFactory.get_gateway(payment.gateway)
        try:
            result = gateway.verify_payment(payment)
        except PaymentGatewayError as exc:
            payment.mark_as_failed()
            raise PaymentServiceError(str(exc)) from exc

        if result.get("success"):
            payment.mark_as_success(
                ref_id=result.get("ref_id") or "",
                card_pan=result.get("card_pan") or "",
            )
            # سفارش فقط از حالت «در انتظار پرداخت» به «پرداخت‌شده» می‌رود؛ اگر به هر دلیلی
            # (مثلاً verify دوباره) این متد دوباره صدا زده شود، وضعیت سفارش را خراب نمی‌کند.
            if order.status == Order.Status.PENDING_PAYMENT:
                order.status = Order.Status.PAID
                order.paid_at = timezone.now()
                order.save(update_fields=["status", "paid_at", "updated_at"])
        else:
            payment.mark_as_failed()
            if order.status == Order.Status.PENDING_PAYMENT:
                order.status = Order.Status.FAILED
                order.save(update_fields=["status", "updated_at"])

        return payment
