from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.cart.models import Cart
from apps.store.models import Product, ProductVariant
from .models import Order, OrderItem
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    ShippingEstimateRequestSerializer
)
from .services import cancel_order_and_restore_stock
from .shipping import calculate_pishtaz_shipping_cost, calculate_total_weight_grams


@extend_schema(tags=['Orders'], summary='لیست سفارش‌های کاربر جاری')
class OrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


@extend_schema(tags=['Orders'], summary='جزئیات یک سفارش')
class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


@extend_schema(
    tags=['Orders'],
    summary='ثبت سفارش جدید از روی سبد خرید فعلی',
    request=OrderCreateSerializer,
    responses={201: OrderDetailSerializer},
)
class OrderCreateView(APIView):
    """
    سفارش را از روی آیتم‌های سبد خرید کاربر جاری می‌سازد:
    - اگر آیتم سبد یک تنوع (رنگ/سایز) مشخص داشته باشد، موجودی و قیمت از همان تنوع خوانده می‌شود؛
      در غیر این صورت از خود محصول (برای محصولات بدون تنوع)
    - موجودی مربوطه (تنوع یا محصول) بررسی و کسر می‌شود
    - قیمت و برچسب تنوع در لحظه‌ی خرید در OrderItem ذخیره (snapshot) می‌شود
    - سبد خرید در پایان خالی می‌شود
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            raise ValidationError('سبد خرید شما خالی است.')

        if cart.expire_if_needed():
            raise ValidationError(
                'مهلت ۳۰ دقیقه‌ای سبد خرید شما به پایان رسیده و سبد خالی شده است. لطفاً دوباره محصولات را اضافه کنید.')

        if not cart.items.exists():
            raise ValidationError('سبد خرید شما خالی است.')

        info_serializer = OrderCreateSerializer(data=request.data)
        info_serializer.is_valid(raise_exception=True)

        order = Order.objects.create(user=request.user, **info_serializer.validated_data)
        items_total = 0
        weighted_items = []

        for cart_item in cart.items.select_related('product', 'variant'):
            product = Product.objects.select_for_update().get(id=cart_item.product_id)
            variant = None

            if cart_item.variant_id:
                variant = ProductVariant.objects.select_for_update().get(id=cart_item.variant_id)
                variant_label = variant.color_name + (f' / {variant.size}' if variant.size else '')

                if not variant.is_active or variant.stock < cart_item.quantity:
                    raise ValidationError(f'موجودی «{product.name} - {variant_label}» کافی نیست.')

                unit_price = variant.final_price
            else:
                variant_label = ''

                if not product.is_available or product.stock < cart_item.quantity:
                    raise ValidationError(f'موجودی «{product.name}» کافی نیست.')

                unit_price = product.final_price

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                variant_label=variant_label,
                product_name=product.name,
                unit_price=unit_price,
                quantity=cart_item.quantity,
            )

            if variant:
                variant.stock -= cart_item.quantity
                variant.save(update_fields=['stock'])
            else:
                product.stock -= cart_item.quantity
                product.save(update_fields=['stock'])

            items_total += unit_price * cart_item.quantity
            item_weight_grams = variant.effective_weight_grams if variant else product.weight_grams
            weighted_items.append((item_weight_grams, cart_item.quantity))

        total_weight_grams = calculate_total_weight_grams(weighted_items)
        shipping_cost = calculate_pishtaz_shipping_cost(total_weight_grams, order.province, items_total)

        order.items_total = items_total
        order.shipping_cost = shipping_cost
        order.total_amount = items_total + shipping_cost - order.discount_total
        order.save(update_fields=['items_total', 'shipping_cost', 'total_amount'])
        cart.items.all().delete()

        return Response(OrderDetailSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Orders'],
    summary='پیش‌نمایش هزینه ارسال (پست پیشتاز) سبد خرید فعلی',
    request=ShippingEstimateRequestSerializer,
)
class ShippingEstimateView(APIView):
    """
    بدون ثبت سفارش، هزینه‌ی ارسال پیشتاز را برای سبد خرید فعلی کاربر و استانِ داده‌شده
    محاسبه و برمی‌گرداند - برای نمایش هزینه ارسال در صفحه‌ی سبد خرید/پیش از پرداخت.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ShippingEstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        province = serializer.validated_data['province']

        cart = Cart.objects.filter(user=request.user).first()
        if not cart or cart.is_expired or not cart.items.exists():
            raise ValidationError('سبد خرید شما خالی است.')

        items_total = 0
        weighted_items = []
        for cart_item in cart.items.select_related('product', 'variant'):
            items_total += cart_item.total_price
            weighted_items.append((cart_item.effective_weight_grams, cart_item.quantity))

        total_weight_grams = calculate_total_weight_grams(weighted_items)
        shipping_cost = calculate_pishtaz_shipping_cost(total_weight_grams, province, items_total)

        return Response({
            'items_total': items_total,
            'weight_grams': total_weight_grams,
            'shipping_cost': shipping_cost,
            'total_amount': items_total + shipping_cost,
        })


@extend_schema(tags=['Orders'], summary='لغو سفارش (فقط در وضعیت در انتظار پرداخت)')
class OrderCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_number, *args, **kwargs):
        order = generics.get_object_or_404(
            Order.objects.select_for_update(), order_number=order_number, user=request.user
        )
        if order.status != Order.Status.PENDING_PAYMENT:
            raise ValidationError('فقط سفارش‌های در انتظار پرداخت قابل لغو هستند.')

        cancel_order_and_restore_stock(order)

        return Response(OrderDetailSerializer(order, context={'request': request}).data)
