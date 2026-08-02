import random
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import phone_regex
from apps.store.models import Product


def generate_order_number():
    return str(random.randint(100000, 999999))


class ShippingSettings(models.Model):
    """
    تنظیمات کلی هزینه‌ی ارسال (پست پیشتاز) - این جدول همیشه فقط یک ردیف دارد و از پنل ادمین
    قابل ویرایش است، تا تغییر نرخ‌ها نیاز به تغییر کد/دیپلوی مجدد نداشته باشد.
    """
    extra_cost_per_kg = models.PositiveIntegerField(
        _('هزینه اضافه به ازای هر کیلوگرم مازاد (تومان)'),
        default=20_000,
        help_text=_(
            'اگر وزن مرسوله از بیشترین سقفِ جدول تعرفه بالاتر برود، به ازای هر ۱ کیلوگرم اضافه '
            '(یا کسری از آن) این مقدار روی هزینه‌ی آخرین ردیف جدول افزوده می‌شود.'
        ),
    )

    class Meta:
        verbose_name = _('تنظیمات هزینه ارسال')
        verbose_name_plural = _('تنظیمات هزینه ارسال')

    def __str__(self):
        return str(_('تنظیمات هزینه ارسال'))

    def save(self, *args, **kwargs):
        # این تنظیمات تک‌ردیفی (singleton) است؛ همیشه روی همان ردیف با pk=1 نوشته می‌شود.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # جلوگیری از حذف تنها ردیفِ تنظیمات
        pass

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class ShippingMethod(models.Model):
    name = models.CharField(_('نام روش ارسال'), max_length=100, unique=True)
    code = models.SlugField(_('کد روش ارسال'), max_length=100, unique=True, help_text=_('مثلاً pishtaz یا tipax'))
    description = models.TextField(_('توضیحات'), blank=True)
    estimated_delivery_time = models.CharField(_('زمان تقریبی تحویل'), max_length=100, blank=True,
                                               help_text=_('مثلاً ۲ تا ۴ روز کاری'))
    extra_cost_per_kg = models.PositiveIntegerField(
        _('هزینه هر کیلوگرم مازاد (تومان)'),
        default=0,
        help_text=_(
            'اگر وزن سفارش از بیشترین سقف تعرفه بیشتر شود، '
            'این مبلغ به ازای هر کیلوگرم اضافه محاسبه می‌شود.'
        ),
    )
    is_active = models.BooleanField(_('فعال'), default=True)
    sort_order = models.PositiveSmallIntegerField(_('ترتیب نمایش'), default=0)

    class Meta:
        verbose_name = _('روش ارسال')
        verbose_name_plural = _('روش‌های ارسال')
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class ShippingTariffRow(models.Model):
    shipping_method = models.ForeignKey(
        ShippingMethod,
        verbose_name=_('روش ارسال'),
        related_name='tariff_rows',
        on_delete=models.CASCADE,
    )
    max_weight_grams = models.PositiveIntegerField(_('سقف وزن (گرم)'))
    tehran_price = models.PositiveIntegerField(_('هزینه برای تهران (تومان)'))
    other_price = models.PositiveIntegerField(_('هزینه برای سایر استان‌ها (تومان)'))

    class Meta:
        verbose_name = _('ردیف تعرفه ارسال')
        verbose_name_plural = _('تعرفه‌های وزنی ارسال')
        ordering = [
            'shipping_method_id',
            'max_weight_grams',
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'shipping_method',
                    'max_weight_grams',
                ],
                name='unique_shipping_method_weight_limit',
            ),
        ]

    def __str__(self):
        return (
            f'{self.shipping_method.name} - '
            f'تا {self.max_weight_grams} گرم'
        )


class SavedAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_address',
        verbose_name=_('کاربر')
    )
    title = models.CharField(_("عنوان"), max_length=50, help_text=_("مثلا خانه، محل کار، انبار"))
    receiver_first_name = models.CharField(_('نام گیرنده'), max_length=75, blank=True)
    receiver_last_name = models.CharField(_('نام خانوادگی گیرنده'), max_length=75, blank=True)
    receiver_phone = models.CharField(_("تلفن گیرنده"), max_length=11, validators=[phone_regex])
    province = models.CharField(_("استان"), max_length=100)
    city = models.CharField(_("شهر"), max_length=100)
    address = models.TextField(_('آدرس کامل'))
    postal_code = models.CharField(_('کد پستی'), max_length=10)
    is_default = models.BooleanField(_("آدرس پیش فرض"), default=False)
    created_at = models.DateTimeField(_('تاریخ ثبت'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        verbose_name = 'آدرس ذخیره شده'
        verbose_name_plural = 'آدرس های ذخیره شده'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.receiver_first_name} {self.receiver_last_name} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.is_default:
            SavedAddress.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', _('در انتظار پرداخت')
        PAID = 'paid', _('پرداخت‌شده')
        PROCESSING = 'processing', _('در حال پردازش')
        SHIPPED = 'shipped', _('ارسال‌شده')
        DELIVERED = 'delivered', _('تحویل داده‌شده')
        CANCELLED = 'cancelled', _('لغوشده')
        FAILED = 'failed', _('پرداخت ناموفق')

    order_number = models.CharField(
        _('شماره سفارش'),
        max_length=32,
        unique=True,
        default=generate_order_number,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='orders',
        on_delete=models.PROTECT,
    )
    status = models.CharField(_('وضعیت'), max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    receiver_first_name = models.CharField(_('نام گیرنده'), max_length=75, blank=True)
    receiver_last_name = models.CharField(_('نام خانوادگی گیرنده'), max_length=75, blank=True)
    receiver_phone = models.CharField(_('تلفن گیرنده'), max_length=11, validators=[phone_regex])
    province = models.CharField(_('استان'), max_length=100)
    city = models.CharField(_('شهر'), max_length=100)
    address = models.TextField(_('آدرس کامل'))
    postal_code = models.CharField(_('کد پستی'), max_length=10)
    items_total = models.PositiveIntegerField(_('جمع قیمت کالاها (تومان)'), default=0)
    shipping_method = models.ForeignKey(
        ShippingMethod,
        verbose_name=_('روش ارسال'),
        related_name='orders',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    shipping_method_name = models.CharField(_('نام روش ارسال در لحظه سفارش'), max_length=100, blank=True)
    total_weight_grams = models.PositiveIntegerField(_('وزن کل سفارش (گرم)'), default=0)
    shipping_cost = models.PositiveIntegerField(_('هزینه ارسال (تومان)'), default=0)
    discount_total = models.PositiveIntegerField(_('مجموع تخفیف (تومان)'), default=0)
    total_amount = models.PositiveIntegerField(_('مبلغ نهایی قابل‌پرداخت (تومان)'), default=0)
    customer_note = models.TextField(_('یادداشت مشتری'), blank=True)
    tracking_code = models.CharField(
        _('کد رهگیری پستی'),
        max_length=50,
        blank=True,
        help_text=_(
            'پس از تحویل بسته به اداره پست، این کد توسط ادمین ثبت می‌شود و پیامک اطلاع‌رسانی به مشتری ارسال می‌گردد.'),
    )
    created_at = models.DateTimeField(_('تاریخ ثبت'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)
    paid_at = models.DateTimeField(_('تاریخ پرداخت'), null=True, blank=True)

    class Meta:
        verbose_name = _('سفارش')
        verbose_name_plural = _('سفارش‌ها')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['order_number'])
        ]

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    """
    آیتم سفارش - قیمت و نام محصول در لحظه‌ی خرید snapshot می‌شود
    تا تغییرات بعدی قیمت محصول روی سفارش‌های ثبت‌شده اثر نگذارد.
    اگر محصول در لحظه‌ی خرید تنوع (رنگ/سایز) داشته، همان تنوع انتخابی و برچسبش
    (`variant_label`) هم ذخیره می‌شود تا حتی با حذف بعدی تنوع، در فاکتور/سفارش قابل مشاهده بماند.
    """
    order = models.ForeignKey(Order, verbose_name=_('سفارش'), related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name=_('محصول'), related_name='order_items', on_delete=models.PROTECT)
    variant = models.ForeignKey(
        'store.ProductVariant',
        verbose_name=_('تنوع محصول (رنگ/سایز)'),
        related_name='order_items',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    variant_label = models.CharField(_('برچسب تنوع (در لحظه خرید)'), max_length=100, blank=True)
    product_name = models.CharField(_('نام محصول (در لحظه خرید)'), max_length=255)
    unit_price = models.PositiveIntegerField(_('قیمت واحد (در لحظه خرید)'))
    quantity = models.PositiveIntegerField(_('تعداد'), validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _('آیتم سفارش')
        verbose_name_plural = _('آیتم‌های سفارش')

    def __str__(self):
        label = self.product_name
        if self.variant_label:
            label += f' ({self.variant_label})'
        return f'{label} x{self.quantity}'

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class AdminNotificationPhone(models.Model):
    phone_number = models.CharField(
        _('شماره تلفن مدیر'),
        max_length=11,
        unique=True,
        validators=[phone_regex],
        help_text=_('شماره موبایل به‌صورت ۱۱ رقمی، مثلاً 09121234567'),
    )
    note = models.CharField(_('توضیح (اختیاری)'), max_length=100, blank=True)
    is_active = models.BooleanField(
        _('فعال'),
        default=True,
        help_text=_('در صورت غیرفعال بودن، پیامک اطلاع‌رسانی سفارش به این شماره ارسال نمی‌شود.'),
    )
    created_at = models.DateTimeField(_('تاریخ افزودن'), auto_now_add=True)

    class Meta:
        verbose_name = _('شماره اطلاع‌رسانی مدیر')
        verbose_name_plural = _('شماره‌های اطلاع‌رسانی مدیر')
        ordering = ['-created_at']

    def __str__(self):
        return self.phone_number
