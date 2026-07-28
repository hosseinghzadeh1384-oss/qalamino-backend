import math
import re
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from apps.store.models import Product
from django_ckeditor_5.fields import CKEditor5Field

WORDS_PER_MINUTE = 200  # برای تخمین زمان مطالعه


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('تاریخ ایجاد'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاریخ بروزرسانی'), auto_now=True)

    class Meta:
        abstract = True


class ArticleCategory(TimeStampedModel):
    name = models.CharField(_('نام دسته‌بندی'), max_length=150)
    slug = models.SlugField(_('اسلاگ'), max_length=170, unique=True, blank=True)
    description = models.TextField(_('توضیحات'), blank=True)
    order = models.PositiveSmallIntegerField(_('ترتیب نمایش'), default=0)
    is_active = models.BooleanField(_('فعال'), default=True)

    class Meta:
        verbose_name = _('دسته‌بندی مقاله')
        verbose_name_plural = _('دسته‌بندی‌های مقاله')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(_('نام تگ'), max_length=60, unique=True)
    slug = models.SlugField(_('اسلاگ'), max_length=80, unique=True, blank=True)

    class Meta:
        verbose_name = _('تگ')
        verbose_name_plural = _('تگ‌ها')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class Article(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', _('پیش‌نویس')
        SCHEDULED = 'scheduled', _('زمان‌بندی‌شده')
        PUBLISHED = 'published', _('منتشرشده')
        ARCHIVED = 'archived', _('بایگانی‌شده')

    title = models.CharField(_('عنوان'), max_length=255)
    slug = models.SlugField(_('اسلاگ'), max_length=280, unique=True, blank=True)
    category = models.ForeignKey(
        ArticleCategory,
        verbose_name=_('دسته‌بندی'),
        related_name='articles',
        on_delete=models.PROTECT,
    )
    tags = models.ManyToManyField(Tag, verbose_name=_('تگ‌ها'), related_name='articles', blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('نویسنده'),
        related_name='articles',
        on_delete=models.PROTECT,
        limit_choices_to={'is_staff': True},
    )
    excerpt = models.CharField(_('خلاصه'), max_length=500, blank=True)
    content = CKEditor5Field(verbose_name="متن مقاله", config_name="extends")
    featured_image = models.ImageField(_('تصویر شاخص'), upload_to='articles/', blank=True, null=True)
    status = models.CharField(_('وضعیت'), max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(_('تاریخ انتشار'), null=True, blank=True, db_index=True)
    is_featured = models.BooleanField(_('مقاله ویژه'), default=False)
    views_count = models.PositiveIntegerField(_('تعداد بازدید'), default=0, editable=False)
    reading_time_minutes = models.PositiveSmallIntegerField(_('زمان مطالعه (دقیقه)'), default=1, editable=False)
    meta_title = models.CharField(_('عنوان سئو'), max_length=255, blank=True)
    meta_description = models.CharField(_('توضیحات سئو'), max_length=300, blank=True)
    related_products = models.ManyToManyField(
        Product,
        verbose_name=_('محصولات مرتبط'),
        related_name='related_articles',
        blank=True,
    )

    class Meta:
        verbose_name = _('مقاله')
        verbose_name_plural = _('مقالات')
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)

        if not self.excerpt and self.content:
            self.excerpt = self._build_excerpt()

        self.reading_time_minutes = self._estimate_reading_time()

        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    def _build_excerpt(self, max_length=300):
        plain_text = re.sub(r'<[^>]+>', ' ', self.content)  # اگر محتوا HTML باشد، تگ‌ها را حذف می‌کند
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        if len(plain_text) <= max_length:
            return plain_text
        return plain_text[:max_length].rsplit(' ', 1)[0] + '…'

    def _estimate_reading_time(self):
        plain_text = re.sub(r'<[^>]+>', ' ', self.content or '')
        word_count = len(plain_text)
        return max(1, math.ceil(word_count / WORDS_PER_MINUTE))

    @property
    def is_published(self):
        return (
                self.status == self.Status.PUBLISHED
                and
                (self.published_at is None or self.published_at <= timezone.now())
        )


class Comment(TimeStampedModel):
    article = models.ForeignKey(Article, verbose_name=_('مقاله'), related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('کاربر'),
        related_name='article_comments',
        on_delete=models.CASCADE,
    )
    parent = models.ForeignKey(
        'self',
        verbose_name=_('پاسخ به'),
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE,
    )
    content = models.TextField(_('متن نظر'), max_length=2000)
    is_approved = models.BooleanField(_('تایید شده'), default=False)

    class Meta:
        verbose_name = _('نظر')
        verbose_name_plural = _('نظرات')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['article', 'is_approved'])
        ]

    def __str__(self):
        return f'نظر {self.user} روی «{self.article.title}»'


class ArticleLike(models.Model):
    article = models.ForeignKey(Article, verbose_name=_('مقاله'), related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('کاربر'), on_delete=models.CASCADE)
    created_at = models.DateTimeField(_('تاریخ لایک'), auto_now_add=True)

    class Meta:
        verbose_name = _('لایک مقاله')
        verbose_name_plural = _('لایک‌های مقاله')
        constraints = [models.UniqueConstraint(fields=['article', 'user'], name='unique_article_like')]

    def __str__(self):
        return f'{self.user} لایک کرد: {self.article.title}'
