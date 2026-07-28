from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import Order, OrderItem, ShippingSettings, ShippingTariffRow


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'variant_label', 'product_name', 'unit_price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'status', 'total_amount', 'created_at', 'paid_at')
    list_filter = ('status',)
    search_fields = ('order_number', 'user__phone_number', 'receiver_phone')
    readonly_fields = ('order_number', 'items_total', 'total_amount', 'created_at', 'updated_at', 'paid_at')
    inlines = [OrderItemInline]


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
