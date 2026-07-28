from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.IntegerField(read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            'id', 'product', 'product_name', 'variant', 'variant_label',
            'unit_price', 'quantity', 'total_price', 'product_slug',
        )
        read_only_fields = ('product_name', 'variant_label', 'unit_price')


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('id', 'order_number', 'status', 'total_amount', 'created_at')


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'status',
            'receiver_full_name', 'receiver_phone', 'province', 'city', 'address', 'postal_code',
            'items', 'items_total', 'shipping_cost', 'discount_total', 'total_amount',
            'customer_note', 'created_at', 'paid_at',
        )
        read_only_fields = (
            'order_number', 'status', 'items_total', 'shipping_cost',
            'discount_total', 'total_amount', 'created_at', 'paid_at',
        )


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'receiver_full_name', 'receiver_phone', 'province',
            'city', 'address', 'postal_code', 'customer_note',
        )


class ShippingEstimateRequestSerializer(serializers.Serializer):
    """برای پیش‌نمایش هزینه‌ی ارسال سبد خرید فعلی، پیش از ثبت نهایی سفارش"""
    province = serializers.CharField(max_length=100)
