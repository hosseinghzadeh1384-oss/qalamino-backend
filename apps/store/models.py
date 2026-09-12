from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Min, Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field
from django.core.exceptions import ValidationError


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class SKUCounter(models.Model):
    next_value = models.PositiveBigIntegerField(default=100)

    class Meta:
        verbose_name = _('شمارنده SKU')
        verbose_name_plural = _('شمارنده SKU')

    def __str__(self):
        return str(self.next_value)


def generate_unique_sku():
    with transaction.atomic():
        SKUCounter.objects.get_or_create(pk=1, defaults={'next_value': 100})
        counter = SKUCounter.objects.select_for_update().get(pk=1)
        candidate = max(counter.next_value, 100)

        while (
                Product.objects.filter(sku=str(candidate)).exists()
                or ProductVariant.objects.filter(sku=str(candidate)).exists()
        ):
            candidate += 1

        counter.next_value = candidate + 1
        counter.save(update_fields=['next_value'])

        return str(candidate)


class Category(TimeStampedModel):
    name = models.CharField(_('نام دسته‌بندی'), max_length=150)
    slug = models.SlugField(_('اسلاگ'), max_length=170, unique=True, blank=True, allow_unicode=True)
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
    slug = models.SlugField(_('اسلاگ'), max_length=170, unique=True, blank=True, allow_unicode=True)
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

    class VariantType(models.TextChoices):
        NONE = 'none', _('بدون تنوع')
        COLOR = 'color', _('رنگ')
        DESIGN = 'design', _('طرح')
        COLOR_DESIGN = 'color_design', _('رنگ و طرح')

    name = models.CharField(_('نام محصول'), max_length=255)
    slug = models.SlugField(_('اسلاگ'), max_length=280, unique=True, blank=True, allow_unicode=True)
    category = models.ForeignKey(Category, verbose_name=_('دسته‌بندی'), related_name='products',
                                 on_delete=models.PROTECT)
    categories = models.ManyToManyField(Category, verbose_name=_('دسته‌بندی‌های بیشتر'),
                                        related_name='multi_category_products', blank=True)
    brand = models.ForeignKey(Brand, verbose_name=_('برند'), related_name='products', on_delete=models.PROTECT,
                              null=True, blank=True)
    description = CKEditor5Field(_('توضیحات محصول'), config_name='extends', blank=True)
    meta_title = models.CharField(_('عنوان سئو'), max_length=255, blank=True)
    meta_description = models.TextField(_('توضیحات سئو'), max_length=300, blank=True)
    sku = models.CharField(_('کد کالا (SKU)'), max_length=64, unique=True, blank=True, editable=False)
    price = models.PositiveIntegerField(_('قیمت (تومان)'), validators=[MinValueValidator(0)])
    discount_price = models.PositiveIntegerField(
        _('قیمت با تخفیف (تومان)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(_('موجودی انبار'), default=0, validators=[MinValueValidator(0)])
    status = models.CharField(_('وضعیت'), max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    variant_type = models.CharField(
        _('نوع تنوع'),
        max_length=20,
        choices=VariantType.choices,
        default=VariantType.NONE,
        help_text=_(
            'اگر محصول تنوع ندارد «بدون تنوع» را انتخاب کنید. '
            'برای محصولاتی مثل خودکار رنگ و برای محصولاتی مثل دفتر با جلدهای مختلف طرح را انتخاب کنید.'
        ),
    )
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

        if self._state.adding or not self.sku:
            self.sku = generate_unique_sku()

        super().save(*args, **kwargs)

    @property
    def final_price(self):
        if self.has_variants:
            variant_prices = [
                variant.final_price
                for variant in self.variants.all()
                if variant.is_active
            ]

            if variant_prices:
                return min(variant_prices)

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
        active_variants = [
            variant
            for variant in self.variants.all()
            if variant.is_active
        ]

        prices = [
            variant.price
            for variant in active_variants
        ]

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
    color_name = models.CharField(_('نام رنگ'), max_length=50, blank=True, null=True)
    color_code = models.CharField(_('کد رنگ (Hex)'), max_length=7, blank=True, help_text=_('مثال: #FF0000'))
    design_name = models.CharField(_('نام طرح'), max_length=50, blank=True)
    sku = models.CharField(_('کد کالا (SKU)'), max_length=64, unique=True, blank=True, editable=False)
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
        ordering = [
            'color_name',
            'design_name',
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'product',
                    'color_name',
                    'design_name',
                ],
                name='unique_product_color_design')
        ]
        indexes = [
            models.Index(fields=['product', 'color_name']),
        ]

    @property
    def display_name(self):
        parts = []

        if self.color_name:
            parts.append(self.color_name.strip())

        if self.design_name:
            parts.append(self.design_name.strip())

        if parts:
            return ' / '.join(parts)

        return 'تنوع محصول'

    def clean(self):
        super().clean()

        if not self.product_id:
            return

        variant_type = self.product.variant_type

        color_name = (self.color_name or '').strip()
        color_code = (self.color_code or '').strip()
        design_name = (self.design_name or '').strip()

        if variant_type == Product.VariantType.NONE:
            raise ValidationError({
                'product': 'این محصول روی حالت «بدون تنوع» قرار دارد.'
            })

        if variant_type == Product.VariantType.COLOR:
            if not color_name:
                raise ValidationError({
                    'color_name': 'برای محصول با تنوع رنگ، نام رنگ الزامی است.'
                })

            if design_name:
                raise ValidationError({
                    'design_name': 'این محصول فقط تنوع رنگ دارد و نباید نام طرح داشته باشد.'
                })

        elif variant_type == Product.VariantType.DESIGN:
            if not design_name:
                raise ValidationError({
                    'design_name': 'برای محصول با تنوع طرح، نام طرح الزامی است.'
                })

            if color_name or color_code:
                raise ValidationError(
                    'این محصول فقط تنوع طرح دارد و نباید اطلاعات رنگ داشته باشد.'
                )

        elif variant_type == Product.VariantType.COLOR_DESIGN:
            if not color_name:
                raise ValidationError({
                    'color_name': 'نام رنگ الزامی است.'
                })

            if not design_name:
                raise ValidationError({
                    'design_name': 'نام طرح الزامی است.'
                })

    def __str__(self):
        return f'{self.product.name} - {self.display_name}'

    def save(self, *args, **kwargs):
        if self._state.adding or not self.sku:
            self.sku = generate_unique_sku()

        super().save(*args, **kwargs)

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


def sync_product_from_variants(product_id):
    variants = ProductVariant.objects.filter(product_id=product_id)

    # اگر آخرین Variant حذف شود، موجودی محصول صفر می‌شود
    # تا محصول با موجودی قدیمی قابل خرید نشود.
    if not variants.exists():
        Product.objects.filter(pk=product_id).update(stock=0)
        return

    active_variants = variants.filter(is_active=True)
    aggregates = active_variants.aggregate(total_stock=Sum('stock'), min_price=Min('price'))

    update_data = {
        'stock': aggregates['total_stock'] or 0,
    }

    if aggregates['min_price'] is not None:
        update_data['price'] = aggregates['min_price']

    Product.objects.filter(pk=product_id).update(**update_data)


@receiver(pre_save, sender=ProductVariant)
def product_variant_pre_save(sender, instance, **kwargs):
    instance._previous_product_id = None

    if instance.pk:
        instance._previous_product_id = (
            sender.objects
            .filter(pk=instance.pk)
            .values_list('product_id', flat=True)
            .first()
        )


@receiver(post_save, sender=ProductVariant)
def product_variant_post_save(sender, instance, **kwargs):
    previous_product_id = getattr(instance, '_previous_product_id', None)

    if previous_product_id and previous_product_id != instance.product_id:
        sync_product_from_variants(previous_product_id)

    sync_product_from_variants(instance.product_id)


@receiver(post_delete, sender=ProductVariant)
def product_variant_post_delete(sender, instance, **kwargs):
    sync_product_from_variants(instance.product_id)


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
