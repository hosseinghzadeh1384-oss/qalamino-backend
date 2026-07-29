from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer


class BaseCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        cart.expire_if_needed()
        return cart


@extend_schema(tags=['Cart'], summary='مشاهده سبد خرید فعلی')
class CartDetailView(BaseCartView):
    def get(self, request, *args, **kwargs):
        cart = self.get_cart()
        return Response(CartSerializer(cart, context={'request': request}).data)


@extend_schema(tags=['Cart'], summary='افزودن محصول به سبد خرید', request=CartItemSerializer)
class CartItemAddView(BaseCartView):
    def post(self, request, *args, **kwargs):
        cart = self.get_cart()
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id') or None

        try:
            requested_quantity = int(request.data.get('quantity', 1))
        except (TypeError, ValueError):
            return Response({'quantity': ['تعداد باید یک عدد صحیح باشد.']}, status=status.HTTP_400_BAD_REQUEST)

        existing = None
        if product_id:
            existing = CartItem.objects.filter(cart=cart, product_id=product_id, variant_id=variant_id).first()

        if existing:
            data = {'quantity': existing.quantity + requested_quantity}
            serializer = CartItemSerializer(existing, data=data, partial=True)
        else:
            serializer = CartItemSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save(cart=cart) if not existing else serializer.save()
        cart.refresh_expiry()

        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Cart'],
    summary='بروزرسانی تعداد یک آیتم سبد خرید',
    request=CartItemSerializer,
    responses=CartSerializer
)
class CartItemUpdateView(BaseCartView):
    def patch(self, request, item_id, *args, **kwargs):
        cart = self.get_cart()
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        serializer = CartItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cart.refresh_expiry()

        return Response(CartSerializer(cart, context={'request': request}).data)


@extend_schema(tags=['Cart'], summary='حذف یک آیتم از سبد خرید')
class CartItemRemoveView(BaseCartView):
    def delete(self, request, item_id, *args, **kwargs):
        cart = self.get_cart()
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)


@extend_schema(tags=['Cart'], summary='خالی کردن کامل سبد خرید')
class CartClearView(BaseCartView):
    def delete(self, request, *args, **kwargs):
        cart = self.get_cart()
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
