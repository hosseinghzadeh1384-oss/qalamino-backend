from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.orders.models import Order
from apps.orders.services import cancel_order_and_restore_stock


class Command(BaseCommand):
    """
    سفارش‌های "در انتظار پرداخت" رهاشده (کاربر پرداخت را کامل نکرده) را که بیش
    از ORDER_PENDING_PAYMENT_TIMEOUT_MINUTES دقیقه از ثبتشان گذشته پیدا می‌کند،
    کنسل می‌کند و موجودیِ محصول/تنوعِ رزروشده‌ی آن‌ها را برمی‌گرداند.

    این دستور idempotent است و اجرای مکرر آن (مثلاً هر ۵ دقیقه از طریق cron)
    بی‌خطر است - سفارش‌هایی که از قبل کنسل/پرداخت شده‌اند دوباره لمس نمی‌شوند.

    مثال اجرا:
        python manage.py cancel_stale_orders
        python manage.py cancel_stale_orders --minutes 30
        python manage.py cancel_stale_orders --dry-run
    """

    help = (
        'سفارش‌های "در انتظار پرداخت" که مهلتشان تمام شده را کنسل و '
        'موجودی رزروشده‌ی آن‌ها را برمی‌گرداند.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=None,
            help=(
                'بازنویسی موقت مهلت (دقیقه) برای همین اجرا. اگر داده نشود، از '
                'تنظیمات ORDER_PENDING_PAYMENT_TIMEOUT_MINUTES خوانده می‌شود.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='فقط سفارش‌های واجد شرایط را چاپ کن، هیچ تغییری در دیتابیس اعمال نکن.',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['minutes']
        if timeout_minutes is None:
            timeout_minutes = getattr(settings, 'ORDER_PENDING_PAYMENT_TIMEOUT_MINUTES', 60)

        cutoff = timezone.now() - timedelta(minutes=timeout_minutes)

        stale_order_numbers = list(
            Order.objects.filter(
                status=Order.Status.PENDING_PAYMENT,
                created_at__lt=cutoff,
            ).values_list('order_number', flat=True)
        )

        if not stale_order_numbers:
            self.stdout.write('هیچ سفارش رهاشده‌ای برای کنسل کردن پیدا نشد.')
            return

        if options['dry_run']:
            self.stdout.write(
                f'{len(stale_order_numbers)} سفارش واجد شرایط کنسل شدن هستند (dry-run، تغییری اعمال نشد):'
            )
            for number in stale_order_numbers:
                self.stdout.write(f'  - {number}')
            return

        cancelled_count = 0

        # هر سفارش را در تراکنش/قفل جداگانه پردازش می‌کنیم؛ نه اینکه همه را در
        # یک تراکنش بزرگ قفل کنیم - هم از deadlock احتمالی جلوگیری می‌شود، هم اگر
        # یکی از سفارش‌ها مشکلی داشت، بقیه بی‌تأثیر پردازش می‌شوند.
        for order_number in stale_order_numbers:
            with transaction.atomic():
                # قفل و بررسی مجدد وضعیت داخل تراکنش: اگر همزمان کاربر همین الان
                # در حال verify کردن پرداختش است، این رکورد تا پایان آن تراکنش
                # منتظر می‌ماند و بعد از قفل، وضعیت را دوباره چک می‌کند - پس هرگز
                # یک سفارشِ تازه‌پرداخت‌شده را کنسل نمی‌کنیم.
                order = Order.objects.select_for_update().get(order_number=order_number)
                if cancel_order_and_restore_stock(order):
                    cancelled_count += 1
                    self.stdout.write(f'کنسل شد: {order.order_number}')

        self.stdout.write(
            self.style.SUCCESS(f'{cancelled_count} سفارش رهاشده کنسل و موجودی آن‌ها بازگردانده شد.')
        )
