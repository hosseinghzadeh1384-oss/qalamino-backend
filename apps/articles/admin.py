from django.contrib import admin
from django.utils.translation import ngettext
from .models import Article, ArticleCategory, ArticleLike, Comment, Tag


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('user', 'content', 'is_approved', 'created_at')
    readonly_fields = ('user', 'content', 'created_at')
    show_change_link = True


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'author', 'status', 'is_featured',
        'views_count', 'reading_time_minutes', 'published_at',
    )
    list_filter = ('status', 'is_featured', 'category')
    search_fields = ('title', 'excerpt', 'content')
    autocomplete_fields = ('category', 'author')
    filter_horizontal = ('tags', 'related_products')
    readonly_fields = ('views_count', 'reading_time_minutes', 'created_at', 'updated_at')
    inlines = [CommentInline]

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'tags', 'author')}),
        ('محتوا', {'fields': ('excerpt', 'content', 'featured_image')}),
        ('انتشار', {'fields': ('status', 'published_at', 'is_featured')}),
        ('سئو', {'fields': ('meta_title', 'meta_description'), 'classes': ('collapse',)}),
        ('فروش محتوایی', {'fields': ('related_products',)}),
        ('آمار (فقط خواندنی)', {'fields': ('views_count', 'reading_time_minutes')}),
        ('تاریخ‌ها', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'short_content', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('content', 'user__phone_number', 'article__title')
    actions = ['approve_comments', 'reject_comments']

    def short_content(self, obj):
        return obj.content[:60] + ('…' if len(obj.content) > 60 else '')
    short_content.short_description = 'متن نظر'

    @admin.action(description='تایید نظرات انتخاب‌شده')
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, ngettext(
            '%d نظر تایید شد.', '%d نظر تایید شد.', updated
        ) % updated)

    @admin.action(description='رد کردن (لغو تایید) نظرات انتخاب‌شده')
    def reject_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, ngettext(
            '%d نظر رد شد.', '%d نظر رد شد.', updated
        ) % updated)


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at')
    search_fields = ('article__title', 'user__phone_number')
