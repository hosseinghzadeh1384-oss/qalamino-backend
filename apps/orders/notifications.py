import logging
from django.conf import settings
from django.dispatch import receiver

from apps.accounts.sms import SMSProviderError, get_sms_provider
from apps.orders.models import AdminNotificationPhone

logger = logging.getLogger('apps.orders.notifications')


def _send_lookup_sms(phone_number, template, token, token2='', token3=''):
    if not phone_number:
        return
    try:
        get_sms_provider().send_lookup(phone_number, template, token, token2, token3)
    except SMSProviderError as exc:
        logger.error('ارسال پیامک (الگو %s) به %s ناموفق بود: %s', template, phone_number, exc)


def notify_order_paid(order):
    """
    پس از پرداخت موفق سفارش، هم‌زمان دو پیامک ارسال می‌شود:
    - به مشتری: با الگوی KAVENEGAR_ORDER_PAID_CUSTOMER_TEMPLATE، شامل نام گیرنده و شماره سفارش
    - به مدیر/مدیران: با الگوی KAVENEGAR_ORDER_PAID_ADMIN_TEMPLATE، شامل شماره سفارش و مبلغ سفارش
    """
    receiver_full_name = order.receiver_first_name.strip()
    _send_lookup_sms(
        order.receiver_phone,
        settings.KAVENEGAR_ORDER_PAID_CUSTOMER_TEMPLATE,
        receiver_full_name,
        order.order_number,
    )

    admin_numbers = AdminNotificationPhone.objects.filter(is_active=True).values_list('phone_number', flat=True)
    for admin_phone in admin_numbers:
        _send_lookup_sms(
            admin_phone,
            settings.KAVENEGAR_ORDER_PAID_ADMIN_TEMPLATE,
            order.order_number,
            str(order.total_amount),
        )


def notify_order_shipped(order):
    """
    پس از ثبت کد رهگیری پستی توسط ادمین، به مشتری با الگوی KAVENEGAR_ORDER_SHIPPED_TEMPLATE
    پیامک ارسال می‌شود که شامل نام گیرنده و کد رهگیری است.
    """
    receiver_full_name = f"{order.receiver_first_name} {order.receiver_last_name}"
    _send_lookup_sms(
        order.receiver_phone,
        settings.KAVENEGAR_ORDER_SHIPPED_TEMPLATE,
        receiver_full_name,
        order.tracking_code,
    )
