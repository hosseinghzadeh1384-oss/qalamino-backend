from django.contrib import admin
from django.utils.translation import ngettext
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject_or_type', 'message_type', 'contact_name', 'status', 'created_at')
    list_filter = ('message_type', 'status', 'created_at')
    search_fields = ('full_name', 'phone_number', 'email', 'subject', 'body', 'user__phone_number')
    autocomplete_fields = ('user',)
    actions = ['mark_in_progress', 'mark_answered', 'mark_closed']
    readonly_fields = ('user', 'full_name', 'phone_number', 'email', 'message_type', 'subject', 'body', 'created_at')
    fieldsets = (
        ('اطلاعات فرستنده', {'fields': ('user', 'full_name', 'phone_number', 'email')}),
        ('پیام', {'fields': ('message_type', 'subject', 'body', 'created_at')}),
        ('پیگیری ادمین', {'fields': ('status', 'admin_note')}),
    )

    def contact_name(self, obj):
        return obj.full_name or (obj.user.phone_number if obj.user_id else '—')

    contact_name.short_description = 'نام / شماره فرستنده'

    def subject_or_type(self, obj):
        return obj.subject or obj.get_message_type_display()

    subject_or_type.short_description = 'موضوع'

    @admin.action(description='علامت‌گذاری به‌عنوان «در حال بررسی»')
    def mark_in_progress(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.IN_PROGRESS)
        self.message_user(request, ngettext(
            '%d پیام بروزرسانی شد.', '%d پیام بروزرسانی شد.', updated
        ) % updated)

    @admin.action(description='علامت‌گذاری به‌عنوان «پاسخ داده‌شده»')
    def mark_answered(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.ANSWERED)
        self.message_user(request, ngettext(
            '%d پیام بروزرسانی شد.', '%d پیام بروزرسانی شد.', updated
        ) % updated)

    @admin.action(description='بستن پیام‌های انتخاب‌شده')
    def mark_closed(self, request, queryset):
        updated = queryset.update(status=ContactMessage.Status.CLOSED)
        self.message_user(request, ngettext(
            '%d پیام بروزرسانی شد.', '%d پیام بروزرسانی شد.', updated
        ) % updated)
