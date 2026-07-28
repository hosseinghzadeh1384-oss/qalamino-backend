from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class Banner(TimeStampedModel):
    class Position(models.TextChoices):
        HOME_SLIDER = 'home_slider', _('اسلایدر صفحه اصلی')
        HOME_MIDDLE = 'home_middle', _('میانی صفحه اصلی')
        CATEGORY_TOP = 'category_top', _('بالای صفحه دسته‌بندی')
        APP_POPUP = 'app_popup', _('پاپ‌آپ اپلیکیشن')

    title = models.CharField(
        _('عنوان (داخلی)'),
        max_length=150,
        help_text=_('فقط برای مدیریت در پنل است و به کاربر نمایش داده نمی‌شود.'),
    )
    image = models.ImageField(_('تصویر بنر (وب / دسکتاپ)'), upload_to='banners/')
    mobile_image = models.ImageField(
        _('تصویر بنر (موبایل)'),
        upload_to='banners/mobile/',
        blank=True,
        null=True,
        help_text=_('اختیاری - اگر خالی بماند، همان تصویر اصلی در اپ موبایل هم استفاده می‌شود.'),
    )
    position = models.CharField(
        _('جایگاه نمایش'),
        max_length=20,
        choices=Position.choices,
        default=Position.HOME_SLIDER,
    )
    link_url = models.CharField(
        _('لینک مقصد'),
        max_length=500,
        blank=True,
        help_text=_('آدرس یا مسیری که با ضربه‌زدن روی بنر باز می‌شود (داخلی یا خارجی)'),
    )
    order = models.PositiveSmallIntegerField(_('ترتیب نمایش'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)
    start_at = models.DateTimeField(_('شروع نمایش'), null=True, blank=True)
    end_at = models.DateTimeField(_('پایان نمایش'), null=True, blank=True)

    class Meta:
        verbose_name = _('بنر')
        verbose_name_plural = _('بنرها')
        ordering = ['position', 'order', '-created_at']
        indexes = [
            models.Index(fields=['position', 'is_active']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_position_display()})'

    @property
    def is_currently_visible(self):
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True
