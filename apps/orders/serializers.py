from rest_framework import serializers

from .models import (
    Order,
    OrderItem,
    SavedAddress,
    ShippingMethod,
)


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = (
            'id',
            'name',
            'code',
            'description',
            'estimated_delivery_time',
        )


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.IntegerField(read_only=True)
    product_slug = serializers.CharField(
        source='product.slug',
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_name',
            'variant',
            'variant_label',
            'unit_price',
            'quantity',
            'total_price',
            'product_slug',
        )
        read_only_fields = (
            'product_name',
            'variant_label',
            'unit_price',
        )


class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'id',
            'order_number',
            'status',
            'shipping_method_name',
            'shipping_cost',
            'total_amount',
            'created_at',
        )


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    shipping_method = ShippingMethodSerializer(
        read_only=True,
    )

    class Meta:
        model = Order
        fields = (
            'id',
            'order_number',
            'status',
            'receiver_first_name',
            'receiver_last_name',
            'receiver_phone',
            'province',
            'city',
            'address',
            'postal_code',
            'items',
            'items_total',
            'shipping_method',
            'shipping_method_name',
            'total_weight_grams',
            'shipping_cost',
            'discount_total',
            'total_amount',
            'customer_note',
            'created_at',
            'paid_at',
        )

        read_only_fields = (
            'order_number',
            'status',
            'items_total',
            'shipping_method',
            'shipping_method_name',
            'total_weight_grams',
            'shipping_cost',
            'discount_total',
            'total_amount',
            'created_at',
            'paid_at',
        )


class OrderCreateSerializer(serializers.ModelSerializer):
    saved_address_id = serializers.IntegerField(
        required=False,
        write_only=True,
    )

    shipping_method_id = serializers.IntegerField(
        required=True,
        write_only=True,
    )

    class Meta:
        model = Order

        fields = (
            'saved_address_id',
            'shipping_method_id',
            'receiver_first_name',
            'receiver_last_name',
            'receiver_phone',
            'province',
            'city',
            'address',
            'postal_code',
            'customer_note',
        )

        # این فیلدها در حالت استفاده از saved_address_id
        # نباید قبل از validate اجباری باشند.
        extra_kwargs = {
            'receiver_first_name': {
                'required': False,
                'allow_blank': True,
            },
            'receiver_last_name': {
                'required': False,
                'allow_blank': True,
            },
            'receiver_phone': {
                'required': False,
                'allow_blank': True,
            },
            'province': {
                'required': False,
                'allow_blank': True,
            },
            'city': {
                'required': False,
                'allow_blank': True,
            },
            'address': {
                'required': False,
                'allow_blank': True,
            },
            'postal_code': {
                'required': False,
                'allow_blank': True,
            },
        }

    def validate_shipping_method_id(self, value):
        try:
            shipping_method = (
                ShippingMethod.objects
                .prefetch_related('tariff_rows')
                .get(
                    id=value,
                    is_active=True,
                )
            )

        except ShippingMethod.DoesNotExist:
            raise serializers.ValidationError(
                'روش ارسال انتخاب‌شده وجود ندارد یا غیرفعال است.'
            )

        if not shipping_method.tariff_rows.exists():
            raise serializers.ValidationError(
                'برای روش ارسال انتخاب‌شده تعرفه‌ای ثبت نشده است.'
            )

        return value

    def validate(self, attrs):
        request = self.context['request']

        shipping_method_id = attrs.pop(
            'shipping_method_id',
        )

        shipping_method = ShippingMethod.objects.get(
            id=shipping_method_id,
            is_active=True,
        )

        attrs['shipping_method'] = shipping_method

        saved_address_id = attrs.pop(
            'saved_address_id',
            None,
        )

        # اگر کاربر یک آدرس ذخیره‌شده انتخاب کرده باشد،
        # اطلاعات سفارش مستقیماً از همان آدرس برداشته می‌شود.
        if saved_address_id:
            try:
                saved_address = SavedAddress.objects.get(
                    id=saved_address_id,
                    user=request.user,
                )

            except SavedAddress.DoesNotExist:
                raise serializers.ValidationError({
                    'saved_address_id':
                        'آدرس انتخاب‌شده وجود ندارد.'
                })

            attrs['receiver_first_name'] = (
                saved_address.receiver_first_name
            )

            attrs['receiver_last_name'] = (
                saved_address.receiver_last_name
            )

            attrs['receiver_phone'] = (
                saved_address.receiver_phone
            )

            attrs['province'] = (
                saved_address.province
            )

            attrs['city'] = (
                saved_address.city
            )

            attrs['address'] = (
                saved_address.address
            )

            attrs['postal_code'] = (
                saved_address.postal_code
            )

            return attrs

        # اگر آدرس ذخیره‌شده انتخاب نشده باشد،
        # اطلاعات آدرس جدید همچنان اجباری هستند.
        required_fields = (
            'receiver_first_name',
            'receiver_last_name',
            'receiver_phone',
            'province',
            'city',
            'address',
            'postal_code',
        )

        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({
                    field: 'این فیلد الزامی است.'
                })

        return attrs


class ShippingEstimateRequestSerializer(
    serializers.Serializer
):
    """
    پیش‌نمایش هزینه روش ارسال انتخاب‌شده
    برای سبد خرید فعلی.
    """

    province = serializers.CharField(
        max_length=100,
    )

    shipping_method_id = serializers.IntegerField()

    def validate_shipping_method_id(self, value):
        try:
            shipping_method = ShippingMethod.objects.get(
                id=value,
                is_active=True,
            )

        except ShippingMethod.DoesNotExist:
            raise serializers.ValidationError(
                'روش ارسال انتخاب‌شده وجود ندارد یا غیرفعال است.'
            )

        if not shipping_method.tariff_rows.exists():
            raise serializers.ValidationError(
                'برای روش ارسال انتخاب‌شده تعرفه‌ای ثبت نشده است.'
            )

        return value


class SavedAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAddress

        fields = (
            'id',
            'title',
            'receiver_first_name',
            'receiver_last_name',
            'receiver_phone',
            'province',
            'city',
            'address',
            'postal_code',
            'is_default',
            'created_at',
            'updated_at',
        )

        read_only_fields = (
            'id',
            'created_at',
            'updated_at',
        )

    def create(self, validated_data):
        validated_data['user'] = (
            self.context['request'].user
        )

        return super().create(validated_data)
