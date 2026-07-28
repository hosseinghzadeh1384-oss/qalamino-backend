from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(_('نام دسته‌بندی'), max_length=150)
    slug = models.SlugField(_('اسلاگ'), max_length=170, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        verbose_name=_('دسته‌بندی والد'),
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE,
    )
    image = models.ImageField(_('تصویر'), upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('دسته‌بندی')
        verbose_name_plural = _('دسته‌بندی‌ها')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Brand(TimeStampedModel):
    name = models.CharField(_('نام برند'), max_length=150, unique=True)
    slug = models.SlugField(_('اسلاگ'), max_length=170, unique=True, blank=True)
    logo = models.ImageField(_('لوگو'), upload_to='brands/', blank=True, null=True)
    description = models.TextField(_('توضیحات'), blank=True)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('برند')
        verbose_name_plural = _('برندها')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('پیش‌نویس')
        PUBLISHED = 'published', _('منتشرشده')
        ARCHIVED = 'archived', _('بایگانی‌شده')

    name = models.CharField(_('نام محصول'), max_length=255)
    slug = models.SlugField(_('اسلاگ'), max_length=280, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_('دسته‌بندی'),
        related_name='products',
        on_delete=models.PROTECT,
    )
    brand = models.ForeignKey(
        Brand,
        verbose_name=_('برند'),
        related_name='products',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    description = models.TextField(_('توضیحات'), blank=True)
    sku = models.CharField(_('کد کالا (SKU)'), max_length=64, unique=True)
    price = models.PositiveIntegerField(_('قیمت (تومان)'), validators=[MinValueValidator(0)])
    discount_price = models.PositiveIntegerField(
        _('قیمت با تخفیف (تومان)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(_('موجودی انبار'), default=0, validators=[MinValueValidator(0)])
    status = models.CharField(_('وضعیت'), max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    weight_grams = models.PositiveIntegerField(_('وزن (گرم)'), null=True, blank=True)

    class Meta:
        verbose_name = _('محصول')
        verbose_name_plural = _('محصولات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def is_available(self):
        if self.status != self.Status.PUBLISHED:
            return False
        if self.has_variants:
            return self.variants.filter(is_active=True, stock__gt=0).exists()
        return self.stock > 0

    @property
    def has_variants(self):
        return self.variants.exists()

    @property
    def min_variant_price(self):
        active_variants = [v for v in self.variants.all() if v.is_active]
        prices = [v.final_price for v in active_variants]
        return min(prices) if prices else None

    @property
    def total_stock(self):
        if self.has_variants:
            return sum(v.stock for v in self.variants.all() if v.is_active)
        return self.stock


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name=_('محصول'), related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(_('تصویر'), upload_to='products/')
    alt_text = models.CharField(_('متن جایگزین'), max_length=255, blank=True)
    is_main = models.BooleanField(_('تصویر اصلی'), default=False)
    order = models.PositiveSmallIntegerField(_('ترتیب نمایش'), default=0)

    class Meta:
        verbose_name = _('تصویر محصول')
        verbose_name_plural = _('تصاویر محصول')
        ordering = ['order']

    def __str__(self):
        return f'{self.product.name} - {self.id}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_main:
            (ProductImage.objects.filter(product_id=self.product_id, is_main=True)
             .exclude(pk=self.pk).update(is_main=False)
             )


class ProductVariant(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        verbose_name=_('محصول'),
        related_name='variants',
        on_delete=models.CASCADE,
    )
    color_name = models.CharField(_('نام رنگ'), max_length=50, blank=True)
    color_code = models.CharField(
        _('کد رنگ (Hex)'),
        max_length=7,
        blank=True,
        help_text=_('مثال: #FF0000'),
    )
    size = models.CharField(_('سایز / مشخصه اضافی'), max_length=50, blank=True)
    sku = models.CharField(_('کد کالا (SKU)'), max_length=64, unique=True)
    price = models.PositiveIntegerField(_('قیمت (تومان)'), validators=[MinValueValidator(0)])
    discount_price = models.PositiveIntegerField(
        _('قیمت با تخفیف (تومان)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(_('موجودی انبار'), default=0)
    image = models.ImageField(_('تصویر تنوع'), upload_to='products/variants/', blank=True, null=True)
    is_active = models.BooleanField(_('فعال'), default=True)
    weight_grams = models.PositiveIntegerField(
        _('وزن (گرم)'),
        null=True,
        blank=True,
        help_text=_('اگر خالی بماند، برای محاسبه‌ی هزینه‌ی ارسال از وزن محصول اصلی استفاده می‌شود.'),
    )

    class Meta:
        verbose_name = _('تنوع محصول')
        verbose_name_plural = _('تنوع‌های محصول')
        ordering = ['color_name', 'size']
        constraints = [
            models.UniqueConstraint(fields=['product', 'color_name', 'size'], name='unique_product_color_size'),
        ]
        indexes = [
            models.Index(fields=['product', 'color_name']),
        ]

    def __str__(self):
        label = self.color_name
        if self.size:
            label = f'{label} / {self.size}'
        return f'{self.product.name} - {label}'

    @property
    def final_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def is_available(self):
        return self.is_active and self.stock > 0

    @property
    def effective_weight_grams(self):
        if self.weight_grams is not None:
            return self.weight_grams
        return self.product.weight_grams


class ProductLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='liked_products',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        verbose_name=_('محصول'),
        related_name='likes',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(_('تاریخ لایک'), auto_now_add=True)

    class Meta:
        verbose_name = _('لایک محصول')
        verbose_name_plural = _('لایک‌های محصول')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_product_like'),
        ]

    def __str__(self):
        return f'{self.user} - {self.product}'


class ProductComment(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        verbose_name=_('محصول'),
        related_name='comments',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='product_comments',
        on_delete=models.CASCADE,
    )
    body = models.TextField(_('متن نظر'), max_length=2000)
    is_approved = models.BooleanField(_('تاییدشده'), default=True)

    class Meta:
        verbose_name = _('نظر محصول')
        verbose_name_plural = _('نظرات محصول')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
        ]

    def __str__(self):
        return f'نظر {self.user} روی {self.product}'


class ProductRating(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name=_('محصول'),
        related_name='ratings',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='product_ratings',
        on_delete=models.CASCADE,
    )
    score = models.PositiveSmallIntegerField(_('امتیاز'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(_('تاریخ ثبت'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        verbose_name = _('امتیاز محصول')
        verbose_name_plural = _('امتیازهای محصول')
        constraints = [
            models.UniqueConstraint(fields=['product', 'user'], name='unique_product_rating'),
        ]

    def __str__(self):
        return f'{self.user} به {self.product} امتیاز {self.score} داد'
