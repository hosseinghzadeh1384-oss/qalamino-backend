from django.contrib import admin
from django.utils.html import format_html
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'thumbnail', 'position', 'order', 'is_active', 'start_at', 'end_at')
    list_filter = ('position', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'link_url')
    fieldsets = (
        (None, {'fields': ('title', 'position', 'order', 'is_active')}),
        ('تصاویر', {'fields': ('image', 'mobile_image')}),
        ('لینک', {'fields': ('link_url',)}),
        ('زمان‌بندی نمایش (اختیاری)', {'fields': ('start_at', 'end_at')}),
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.image.url)
        return '—'
    thumbnail.short_description = 'پیش‌نمایش'
