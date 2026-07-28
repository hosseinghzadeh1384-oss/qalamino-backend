from rest_framework import serializers
from .models import Payment, PaymentGateway, PaymentStatus


# ------------------------------------------------
# نمایش اطلاعات Payment
# ------------------------------------------------

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "user",
            "amount",
            "status",
            "gateway",
            "authority",
            "payment_url",
            "ref_id",
            "description",
            "card_pan",
            "paid_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# ------------------------------------------------
# ساخت Payment اولیه قبل از اتصال به درگاه
# ------------------------------------------------

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("order", "gateway")

    def validate_order(self, order):
        user = self.context["request"].user

        if order.user != user:
            raise serializers.ValidationError("این سفارش متعلق به شما نیست.")

        if order.status != order.Status.PENDING_PAYMENT:
            raise serializers.ValidationError("این سفارش در وضعیت قابل‌پرداخت نیست.")
        return order

    def validate(self, attrs):
        order = attrs["order"]

        if order.payments.filter(status=PaymentStatus.SUCCESS).exists():
            raise serializers.ValidationError("این سفارش قبلاً پرداخت شده است.")

        return attrs

    def create(self, validated_data):
        order = validated_data["order"]
        payment = Payment.objects.create(
            user=self.context["request"].user,
            order=order,
            amount=order.total_amount,
            gateway=validated_data["gateway"],
            description=f"پرداخت سفارش {order.order_number}",
        )
        return payment


# ------------------------------------------------
# Verify پرداخت بعد از برگشت از بانک
# ------------------------------------------------

class PaymentVerifySerializer(serializers.Serializer):
    authority = serializers.CharField(max_length=255)

    def validate_authority(self, authority):
        try:
            payment = Payment.objects.get(authority=authority)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("پرداخت پیدا نشد.")

        request = self.context.get("request")
        if request and payment.user_id != request.user.id:
            raise serializers.ValidationError("پرداخت پیدا نشد.")

        if payment.status == PaymentStatus.SUCCESS:
            raise serializers.ValidationError("این پرداخت قبلاً تایید شده است.")

        self.payment = payment

        return authority


# ------------------------------------------------
# دریافت Callback از سیزپی
# ------------------------------------------------
# سیزپی Token را در callback برمی‌گرداند (نه یک فیلد جدا به نام authority)
# بنابراین از آن برای پیدا کردن Payment استفاده می‌شود.

class SizpayCallbackSerializer(serializers.Serializer):
    ResCod = serializers.CharField(max_length=10)
    Message = serializers.CharField(max_length=500, required=False, allow_blank=True)
    Token = serializers.CharField(max_length=3000)

    def validate_Token(self, token):
        try:
            payment = Payment.objects.get(authority=token, gateway=PaymentGateway.SIZPAY)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("پرداخت مربوطه پیدا نشد.")

        self.payment = payment

        return token


# ------------------------------------------------
# دریافت Callback از سپهر
# ------------------------------------------------
# سپهر توکن/authority را در callback برنمی‌گرداند؛ تطبیق بر اساس invoiceid
# (که همان شماره سفارش است) و بودن وضعیت pending انجام می‌شود.

class SepehrCallbackSerializer(serializers.Serializer):
    respcode = serializers.CharField(max_length=10)
    respmsg = serializers.CharField(max_length=500, required=False, allow_blank=True)
    invoiceid = serializers.CharField(max_length=100)
    digitalreceipt = serializers.CharField(max_length=500, required=False, allow_blank=True)
    cardnumber = serializers.CharField(max_length=50, required=False, allow_blank=True)
    rrn = serializers.CharField(max_length=50, required=False, allow_blank=True)
    tracenumber = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate(self, attrs):
        payment = Payment.objects.filter(
            order__order_number=attrs["invoiceid"],
            gateway=PaymentGateway.SEPEHR,
            status=PaymentStatus.PENDING,
        ).order_by("-created_at").first()

        if payment is None:
            raise serializers.ValidationError("پرداخت مربوطه پیدا نشد.")

        self.payment = payment

        return attrs
