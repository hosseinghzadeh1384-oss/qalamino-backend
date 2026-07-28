from django.contrib import admin
from .models import (
    Brand,
    Category,
    Product,
    ProductComment,
    ProductImage,
    ProductLike,
    ProductRating,
    ProductVariant,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        'color_name', 'color_code', 'size', 'sku', 'price', 'discount_price',
        'stock', 'weight_grams', 'is_active',
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'weight_grams', 'discount_price', 'stock', 'status')
    list_filter = ('status', 'category', 'brand')
    search_fields = ('name', 'sku', 'description')
    inlines = [ProductImageInline, ProductVariantInline]
    autocomplete_fields = ('category', 'brand')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color_name', 'size', 'price', 'discount_price', 'stock', 'weight_grams', 'is_active')
    list_filter = ('is_active', 'color_name')
    search_fields = ('product__name', 'sku', 'color_name')
    autocomplete_fields = ('product',)


@admin.register(ProductLike)
class ProductLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__phone_number', 'product__name')
    autocomplete_fields = ('user', 'product')


@admin.register(ProductComment)
class ProductCommentAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'is_approved', 'created_at')
    list_filter = ('is_approved',)
    search_fields = ('product__name', 'user__phone_number', 'body')
    autocomplete_fields = ('user', 'product')


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'score', 'created_at')
    list_filter = ('score',)
    search_fields = ('product__name', 'user__phone_number')
    autocomplete_fields = ('user', 'product')
