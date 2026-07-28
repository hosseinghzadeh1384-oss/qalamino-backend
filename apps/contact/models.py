from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class ContactMessage(TimeStampedModel):
    class MessageType(models.TextChoices):
        REQUEST = 'request', _('درخواست')
        COMPLAINT = 'complaint', _('انتقاد')
        SUGGESTION = 'suggestion', _('پیشنهاد')
        OTHER = 'other', _('سایر')

    class Status(models.TextChoices):
        NEW = 'new', _('جدید')
        IN_PROGRESS = 'in_progress', _('در حال بررسی')
        ANSWERED = 'answered', _('پاسخ داده‌شده')
        CLOSED = 'closed', _('بسته‌شده')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='contact_messages',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    message_type = models.CharField(
        _('نوع پیام'),
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.REQUEST,
    )
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=150, blank=True)
    phone_number = models.CharField(_('شماره تلفن'), max_length=11, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True)
    subject = models.CharField(_('موضوع'), max_length=200, blank=True)
    body = models.TextField(_('متن پیام'), max_length=3000)
    status = models.CharField(
        _('وضعیت پیگیری'),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    admin_note = models.TextField(
        _('یادداشت / پاسخ ادمین'),
        blank=True,
        help_text=_('فقط برای استفاده داخلی تیم پشتیبانی است و به کاربر نمایش داده نمی‌شود.'),
    )

    class Meta:
        verbose_name = _('پیام تماس با ما')
        verbose_name_plural = _('پیام‌های تماس با ما')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['message_type']),
        ]

    def __str__(self):
        who = self.full_name or (self.user.phone_number if self.user_id else 'ناشناس')
        return f'{self.get_message_type_display()} از {who}'
