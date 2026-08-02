from django.contrib import admin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from .models import AdminNotificationPhone, Order, OrderItem, ShippingSettings, ShippingTariffRow, SavedAddress
from .notifications import notify_order_shipped


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'variant_label', 'product_name', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'tracking_code', 'created_at', 'paid_at')
    list_filter = ('status',)
    search_fields = ('order_number', 'user__phone_number', 'receiver_phone', 'tracking_code')
    readonly_fields = ('order_number', 'items_total', 'total_amount', 'created_at', 'updated_at', 'paid_at')
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        # پیامک اطلاع‌رسانیِ تحویل به پست فقط زمانی ارسال می‌شود که کد رهگیری برای اولین‌بار
        # ثبت شود (تا ذخیره‌های بعدیِ فرم، دوباره پیامک تکراری نفرستند).
        should_notify = False
        if change and 'tracking_code' in form.changed_data and obj.tracking_code:
            previous_tracking_code = Order.objects.filter(pk=obj.pk).values_list('tracking_code', flat=True).first()
            if not previous_tracking_code:
                should_notify = True

        super().save_model(request, obj, form, change)

        if should_notify:
            transaction.on_commit(lambda: notify_order_shipped(obj))


@admin.register(ShippingSettings)
class ShippingSettingsAdmin(admin.ModelAdmin):
    """
    این مدل همیشه فقط یک ردیف (singleton) دارد؛ به‌جای نمایش لیست، مستقیماً کاربر را به فرم
    ویرایش همان تک‌ردیف هدایت می‌کنیم و امکان افزودن/حذف ردیف جدید را غیرفعال می‌کنیم.
    """
    fields = ('extra_cost_per_kg',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ShippingSettings.get_solo()
        url = reverse('admin:orders_shippingsettings_change', args=[obj.pk])
        return redirect(url)


@admin.register(ShippingTariffRow)
class ShippingTariffRowAdmin(admin.ModelAdmin):
    list_display = ('max_weight_grams', 'tehran_price', 'other_price')
    ordering = ('max_weight_grams',)


@admin.register(AdminNotificationPhone)
class AdminNotificationPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'note', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('phone_number', 'note')


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'user',
        'receiver_full_name',
        'receiver_phone',
        'province',
        'city',
        'is_default',
        'created_at',
    )
    list_filter = ('province', 'city', 'is_default')
    search_fields = ('title', 'user__phone_number', 'receiver_full_name', 'receiver_phone', 'address')
    autocomplete_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('user', '-is_default', '-created_at')
