from django.db import transaction
from apps.payment.models import PaymentStatus
from apps.store.models import Product, ProductVariant
from .models import Order


@transaction.atomic
def cancel_order_and_restore_stock(order):
    """
    سفارش را کنسل کرده و موجودی آیتم‌های آن را
    به محصول یا تنوع مربوطه برمی‌گرداند.
    """

    if order.status != Order.Status.PENDING_PAYMENT:
        return False

    for item in order.items.select_related(
        'product',
        'variant',
    ):
        product = (
            Product.objects
            .select_for_update()
            .get(pk=item.product_id)
        )

        if item.variant_id:
            variant = (
                ProductVariant.objects
                .select_for_update()
                .get(pk=item.variant_id)
            )

            variant.stock += item.quantity
            variant.save(
                update_fields=['stock']
            )

        else:
            product.stock += item.quantity
            product.save(
                update_fields=['stock']
            )

    order.status = Order.Status.CANCELLED

    order.save(
        update_fields=[
            'status',
            'updated_at',
        ]
    )

    order.payments.filter(
        status=PaymentStatus.PENDING
    ).update(
        status=PaymentStatus.CANCELED
    )

    return True