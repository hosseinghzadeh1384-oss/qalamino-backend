from django.utils import timezone
from rest_framework import serializers
from apps.store.models import Product, ProductVariant
from apps.store.serializers import ProductVariantSerializer
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source='product', queryset=Product.objects.all(), write_only=True)
    variant_id = serializers.PrimaryKeyRelatedField(
        source='variant',
        queryset=ProductVariant.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    variant = ProductVariantSerializer(read_only=True)
    unit_price = serializers.IntegerField(read_only=True)
    total_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = CartItem
        fields = (
            'id', 'product_id', 'variant_id', 'product_name', 'product_slug', 'variant',
            'quantity', 'unit_price', 'total_price',
        )

    def validate(self, attrs):
        product = attrs.get('product') or getattr(self.instance, 'product', None)
        variant = attrs.get('variant', getattr(self.instance, 'variant', None))
        quantity = attrs.get('quantity', getattr(self.instance, 'quantity', 1))

        if variant and product and variant.product_id != product.id:
            raise serializers.ValidationError({'variant_id': ['این تنوع متعلق به این محصول نیست.']})

        if product and product.has_variants and not variant:
            raise serializers.ValidationError({'variant_id': ['برای این محصول باید یک تنوع (مثلاً رنگ) انتخاب کنید.']})

        if variant:
            if not variant.is_available:
                raise serializers.ValidationError('این تنوع از محصول در حال حاضر موجود نیست.')
            if quantity > variant.stock:
                raise serializers.ValidationError(f'موجودی کافی نیست. حداکثر {variant.stock} عدد از این تنوع موجود است.')
        elif product:
            if not product.is_available:
                raise serializers.ValidationError('این محصول در حال حاضر موجود نیست.')
            if quantity > product.stock:
                raise serializers.ValidationError(f'موجودی کافی نیست. حداکثر {product.stock} عدد در انبار موجود است.')

        return attrs


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.IntegerField(read_only=True)
    seconds_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            'id', 'items', 'total_items', 'total_price',
            'expires_at', 'seconds_remaining', 'updated_at',
        )

    def get_seconds_remaining(self, obj):
        if not obj.expires_at:
            return None
        remaining = (obj.expires_at - timezone.now()).total_seconds()
        return max(int(remaining), 0)
