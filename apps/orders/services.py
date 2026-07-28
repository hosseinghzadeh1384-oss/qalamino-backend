from django.db import transaction
from apps.payment.models import PaymentStatus
from .models import Order


@transaction.atomic
def cancel_order_and_restore_stock(order):
    """
    سفارش را کنسل کرده و موجودیِ آیتم‌های آن را به محصول/تنوعِ مربوطه برمی‌گرداند.

    فقط روی سفارش‌های در وضعیت ``pending_payment`` عمل می‌کند؛ برای بقیه‌ی
    وضعیت‌ها هیچ تغییری اعمال نمی‌شود (ایمن در برابر فراخوانی تکراری/همزمان).

    نکته‌ی race condition: فراخوانی‌کننده باید پیش از این تابع، خودِ ``order``
    را با ``select_for_update()`` قفل کرده باشد (همان‌طور که در OrderCancelView
    و دستور مدیریتی cancel_stale_orders انجام می‌شود)، تا اگر همزمان کاربر در
    حال verify کردن پرداخت است، وضعیت سفارش خراب نشود.

    خروجی: True اگر سفارش واقعاً کنسل شد، False اگر سفارش از قبل در وضعیت
    دیگری بود و کاری انجام نشد.
    """
    if order.status != Order.Status.PENDING_PAYMENT:
        return False

    for item in order.items.select_related('product', 'variant'):
        if item.variant_id:
            item.variant.stock += item.quantity
            item.variant.save(update_fields=['stock'])
        else:
            item.product.stock += item.quantity
            item.product.save(update_fields=['stock'])

    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status', 'updated_at'])
    order.payments.filter(status=PaymentStatus.PENDING).update(status=PaymentStatus.CANCELED)

    return True
