from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['-date_joined']
    list_display = ('phone_number', 'full_name', 'is_phone_verified', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_phone_verified')
    search_fields = ('phone_number', 'full_name', 'email')

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات شخصی', {'fields': ('full_name', 'email')}),
        ('دسترسی‌ها',
         {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_phone_verified', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_used',)
    search_fields = ('phone_number',)
    readonly_fields = ('phone_number', 'code_hash', 'is_used', 'attempts', 'created_at', 'expires_at')

    def has_add_permission(self, request):
        return False
