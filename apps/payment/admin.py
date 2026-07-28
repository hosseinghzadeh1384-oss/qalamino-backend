from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "gateway", "ref_id", "created_at")
    list_filter = ("status", "gateway", "created_at")
    search_fields = ("ref_id", "authority", "user__phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("id", "authority", "ref_id", "paid_at", "created_at", "updated_at", "extra_data")
    fieldsets = (
        (
            "اطلاعات پرداخت",
            {
                "fields": ("id", "user", "order", "amount", "status", "gateway")
            }
        ),
        (
            "اطلاعات درگاه پرداخت",
            {
                "fields": ("authority", "ref_id", "payment_url", "extra_data")
            }
        ),
        (
            "تاریخ",
            {
                "fields": ("paid_at", "created_at", "updated_at")
            }
        ),
    )
