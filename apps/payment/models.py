import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from apps.orders.models import Order
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    PENDING = "pending", _("در انتظار پرداخت")
    SUCCESS = "success", _("پرداخت موفق")
    FAILED = "failed", _("پرداخت ناموفق")
    CANCELED = "canceled", _("لغو شده")


class PaymentGateway(models.TextChoices):
    SIZPAY = "sizpay", _("سیزپی")
    SEPEHR = "sepehr", _("بانک سپهر (صادرات)")


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="شناسه")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments", verbose_name="سفارش")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="کاربر"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=0, verbose_name="مبلغ")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="وضعیت پرداخت"
    )
    gateway = models.CharField(max_length=20, choices=PaymentGateway.choices, verbose_name="درگاه پرداخت")
    authority = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="کد تراکنش")
    payment_url = models.URLField(max_length=500, null=True, blank=True, verbose_name="لینک پرداخت")
    ref_id = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="شماره مرجع")
    description = models.CharField(max_length=255, blank=True, verbose_name="توضیحات")
    card_pan = models.CharField(max_length=20, blank=True, verbose_name="شماره کارت")
    extra_data = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات تکمیلی")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت ها"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["authority"]),
            models.Index(fields=["ref_id"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status=PaymentStatus.SUCCESS),
                name="unique_success_payment_per_order",
            )
        ]

    def __str__(self):
        return f"Order #{self.order.id} - {self.get_status_display()}"

    def mark_as_success(self, ref_id: str, card_pan: str = ""):
        self.status = PaymentStatus.SUCCESS
        self.ref_id = ref_id
        self.card_pan = card_pan
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "ref_id", "card_pan", "paid_at", "updated_at"])

    def mark_as_failed(self):
        self.status = PaymentStatus.FAILED
        self.save(update_fields=["status", "updated_at"])
