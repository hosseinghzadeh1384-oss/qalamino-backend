import secrets
import string
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager

phone_regex = RegexValidator(regex=r'^09\d{9}$', message='شماره تلفن باید به فرمت 09xxxxxxxxx باشد.')


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        _('شماره تلفن'),
        max_length=11,
        unique=True,
        validators=[phone_regex],
        db_index=True,
    )
    full_name = models.CharField(_('نام و نام خانوادگی'), max_length=150, blank=True)
    email = models.EmailField(_('ایمیل'), blank=True, null=True)
    is_phone_verified = models.BooleanField(_('تایید شماره تلفن'), default=False)
    is_active = models.BooleanField(_('فعال'), default=True)
    is_staff = models.BooleanField(_('دسترسی ادمین'), default=False)
    date_joined = models.DateTimeField(_('تاریخ عضویت'), default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('کاربر')
        verbose_name_plural = _('کاربران')
        ordering = ['-date_joined']

    def __str__(self):
        return self.phone_number


class OTPCode(models.Model):
    phone_number = models.CharField(_('شماره تلفن'), max_length=11, validators=[phone_regex], db_index=True)
    code_hash = models.CharField(_('کد (هش‌شده)'), max_length=128)
    expires_at = models.DateTimeField(_('تاریخ انقضا'))
    is_used = models.BooleanField(_('استفاده‌شده'), default=False)
    attempts = models.PositiveSmallIntegerField(_('تعداد تلاش‌های ناموفق'), default=0)
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)

    class Meta:
        verbose_name = _('کد یک‌بارمصرف')
        verbose_name_plural = _('کدهای یک‌بارمصرف')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'is_used'])
        ]

    def __str__(self):
        return f'OTP برای {self.phone_number}'

    def set_code(self, raw_code):
        self.code_hash = make_password(raw_code)

    def check_code(self, raw_code):
        return check_password(raw_code, self.code_hash)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def generate_for(cls, phone_number):
        raw_code = ''.join(secrets.choice(string.digits) for _ in range(settings.OTP_CODE_LENGTH))
        otp = cls(
            phone_number=phone_number,
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
        )
        otp.set_code(raw_code)
        otp.save()
        return otp, raw_code

    @classmethod
    def get_latest_active(cls, phone_number):
        return cls.objects.filter(phone_number=phone_number, is_used=False).order_by('-created_at').first()
