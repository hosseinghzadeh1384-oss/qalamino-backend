from django.contrib import admin
from django import forms
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


class ColorPickerWidget(forms.TextInput):
    input_type = 'color'


class ProductVariantAdminForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = '__all__'
        widgets = {
            'color_code': ColorPickerWidget(
                attrs={
                    'style': 'width: 80px; height: 40px; padding: 2px; cursor: pointer;',
                    'title': 'انتخاب رنگ',
                }
            ),
        }


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    form = ProductVariantAdminForm
    extra = 1
    readonly_fields = ('sku',)
    fields = (
        'color_name',
        'color_code',
        'size',
        'sku',
        'price',
        'discount_price',
        'stock',
        'weight_grams',
        'image',
        'is_active',
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'sku',
        'category',
        'brand',
        'price',
        'weight_grams',
        'discount_price',
        'stock',
        'status',
    )

    list_filter = (
        'status',
        'category',
        'brand',
    )

    search_fields = (
        'name',
        'sku',
        'description',
    )

    inlines = [
        ProductImageInline,
        ProductVariantInline,
    ]

    autocomplete_fields = (
        'category',
        'brand',
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = ['sku']

        if obj and obj.has_variants:
            readonly.extend([
                'price',
                'stock',
            ])

        return tuple(readonly)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    form = ProductVariantAdminForm
    readonly_fields = ('sku',)

    list_display = (
        'product',
        'sku',
        'color_name',
        'size',
        'price',
        'discount_price',
        'stock',
        'weight_grams',
        'is_active',
    )

    list_filter = (
        'is_active',
        'color_name',
    )

    search_fields = (
        'product__name',
        'sku',
        'color_name',
    )

    autocomplete_fields = (
        'product',
    )

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
