from rest_framework import serializers
from .models import Order, OrderItem, SavedAddress


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
    saved_address_id = serializers.IntegerField(
        required=False,
        write_only=True,
    )

    class Meta:
        model = Order
        fields = (
            "saved_address_id",
            "receiver_full_name",
            "receiver_phone",
            "province",
            "city",
            "address",
            "postal_code",
            "customer_note",
        )

    def validate(self, attrs):
        request = self.context["request"]
        saved_address_id = attrs.pop("saved_address_id", None)

        if saved_address_id:
            try:
                saved_address = SavedAddress.objects.get(id=saved_address_id, user=request.user)
            except SavedAddress.DoesNotExist:
                raise serializers.ValidationError({"saved_address_id": "آدرس انتخاب شده وجود ندارد."})

            attrs["receiver_full_name"] = saved_address.receiver_full_name
            attrs["receiver_phone"] = saved_address.receiver_phone
            attrs["province"] = saved_address.province
            attrs["city"] = saved_address.city
            attrs["address"] = saved_address.address
            attrs["postal_code"] = saved_address.postal_code
            return attrs

        required_fields = ("receiver_full_name", "receiver_phone", "province", "city", "address", "postal_code")

        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({field: "این فیلد الزامی است."})
        return attrs


class ShippingEstimateRequestSerializer(serializers.Serializer):
    """برای پیش‌نمایش هزینه‌ی ارسال سبد خرید فعلی، پیش از ثبت نهایی سفارش"""
    province = serializers.CharField(max_length=100)


class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress
        fields = (
            "id",
            "title",
            "receiver_full_name",
            "receiver_phone",
            "province",
            "city",
            "address",
            "postal_code",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
