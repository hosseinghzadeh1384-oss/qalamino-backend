from datetime import timedelta
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.store.models import Product, ProductVariant

# محدودیت زمانی خرید: تعداد دقیقه‌ای که سبد خرید بدون تمدید معتبر می‌ماند
CART_EXPIRY_MINUTES = getattr(settings, 'CART_EXPIRY_MINUTES', 30)


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='cart',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)
    expires_at = models.DateTimeField(_('تاریخ انقضا سبد خرید'), null=True, blank=True)

    class Meta:
        verbose_name = _('سبد خرید')
        verbose_name_plural = _('سبدهای خرید')

    def __str__(self):
        return f'سبد خرید {self.user.phone_number}'

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def is_expired(self):
        return bool(self.expires_at) and timezone.now() > self.expires_at

    def refresh_expiry(self, commit=True):
        self.expires_at = timezone.now() + timedelta(minutes=CART_EXPIRY_MINUTES)
        if commit:
            self.save(update_fields=['expires_at'])

    def expire_if_needed(self):
        """
        اگر مدت‌زمان مجاز خرید سپری شده باشد، آیتم‌های سبد را خالی می‌کند.
        خروجی: True اگر سبد در همین فراخوانی منقضی و خالی شده باشد.
        """
        if self.is_expired:
            self.items.all().delete()
            self.expires_at = None
            self.save(update_fields=['expires_at'])
            return True
        return False


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, verbose_name=_('سبد خرید'), related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name=_('محصول'), related_name='cart_items', on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant,
        verbose_name=_('تنوع محصول (رنگ/سایز)'),
        related_name='cart_items',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text=_('اگر محصول تنوع (رنگ/سایز) داشته باشد، انتخاب آن اجباری است.'),
    )
    quantity = models.PositiveIntegerField(_('تعداد'), default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(_('تاریخ افزودن'), auto_now_add=True)

    class Meta:
        verbose_name = _('آیتم سبد خرید')
        verbose_name_plural = _('آیتم‌های سبد خرید')
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product', 'variant'], name='unique_cart_product_variant'),
        ]

    def __str__(self):
        label = self.product.name
        if self.variant_id:
            label += f' ({self.variant.display_name})'
        return f'{label} x {self.quantity}'

    @property
    def unit_price(self):
        if self.variant_id:
            return self.variant.final_price
        return self.product.final_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def available_stock(self):
        if self.variant_id:
            return self.variant.stock
        return self.product.stock

    @property
    def is_purchasable(self):
        if self.variant_id:
            return self.variant.is_available
        return self.product.is_available

    @property
    def effective_weight_grams(self):
        """
        وزن مؤثر این آیتم برای محاسبه‌ی هزینه‌ی ارسال - اگر تنوع انتخاب‌شده وزن مخصوص به خود داشته باشد همان، وگرنه وزن محصول اصلی.
        """
        if self.variant_id:
            return self.variant.effective_weight_grams
        return self.product.weight_grams
