"""
محاسبه وزن و هزینه ارسال سفارش.

هر روش ارسال جدول تعرفه وزنی مستقل و هزینه وزن مازاد مخصوص خود را دارد.
وزن سفارش از وزن محصول یا تنوع محصول و تعداد آن محاسبه می‌شود.
"""

import math

from django.conf import settings


def calculate_total_weight_grams(weighted_items):
    """
    وزن کل سفارش را برحسب گرم محاسبه می‌کند.

    weighted_items:
        لیستی از زوج‌های (weight_grams, quantity)

    اگر وزن محصول یا تنوع ثبت نشده باشد، مقدار
    DEFAULT_PRODUCT_WEIGHT_GRAMS استفاده می‌شود.
    """

    default_weight = getattr(
        settings,
        'DEFAULT_PRODUCT_WEIGHT_GRAMS',
        200,
    )

    total_weight = 0

    for weight_grams, quantity in weighted_items:
        final_weight = weight_grams or default_weight
        total_weight += final_weight * quantity

    return total_weight


def _is_tehran(province):
    """
    بررسی می‌کند استان مقصد تهران است یا خیر.
    """

    tehran_name = getattr(
        settings,
        'PISHTAZ_TEHRAN_PROVINCE_NAME',
        'تهران',
    )

    return (province or '').strip() == tehran_name


def calculate_shipping_cost(
        total_weight_grams,
        province,
        shipping_method,
        items_total=0,
):
    """
    هزینه ارسال یک روش مشخص را محاسبه می‌کند.

    ورودی‌ها:
        total_weight_grams:
            وزن کل سفارش به گرم.

        province:
            استان مقصد.

        shipping_method:
            نمونه‌ای از مدل ShippingMethod.

        items_total:
            جمع قیمت کالاها برای بررسی ارسال رایگان.

    خروجی:
        هزینه ارسال به تومان.

    خطا:
        اگر روش ارسال غیرفعال باشد یا تعرفه‌ای نداشته باشد،
        ValueError ایجاد می‌شود.
    """

    from .models import ShippingTariffRow

    if shipping_method is None:
        raise ValueError('روش ارسال مشخص نشده است.')

    if not shipping_method.is_active:
        raise ValueError('روش ارسال انتخاب‌شده غیرفعال است.')

    free_shipping_threshold = getattr(
        settings,
        'FREE_SHIPPING_THRESHOLD',
        0,
    )

    if (
            free_shipping_threshold
            and items_total >= free_shipping_threshold
    ):
        return 0

    tariff_table = list(
        ShippingTariffRow.objects.filter(
            shipping_method=shipping_method,
        )
        .order_by('max_weight_grams')
        .values_list(
            'max_weight_grams',
            'tehran_price',
            'other_price',
        )
    )

    if not tariff_table:
        raise ValueError(
            'برای روش ارسال انتخاب‌شده تعرفه‌ای ثبت نشده است.'
        )

    if total_weight_grams <= 0:
        total_weight_grams = getattr(
            settings,
            'DEFAULT_PRODUCT_WEIGHT_GRAMS',
            200,
        )

    is_tehran = _is_tehran(province)

    for (
            max_weight_grams,
            tehran_price,
            other_price,
    ) in tariff_table:
        if total_weight_grams <= max_weight_grams:
            if is_tehran:
                return tehran_price

            return other_price

    (
        last_max_weight_grams,
        last_tehran_price,
        last_other_price,
    ) = tariff_table[-1]

    extra_weight_grams = (
            total_weight_grams - last_max_weight_grams
    )

    extra_kg_steps = math.ceil(
        extra_weight_grams / 1000
    )

    extra_cost = (
            extra_kg_steps
            * shipping_method.extra_cost_per_kg
    )

    base_price = (
        last_tehran_price
        if is_tehran
        else last_other_price
    )

    return base_price + extra_cost


def calculate_pishtaz_shipping_cost(
        total_weight_grams,
        province,
        items_total=0,
):
    """
    تابع موقت سازگاری با API فعلی.

    تا زمانی که views.py در مرحله بعد به روش ارسال انتخابی
    متصل شود، درخواست‌های قبلی همچنان کار می‌کنند.
    """

    from .models import ShippingMethod

    shipping_method = ShippingMethod.objects.filter(
        code='pishtaz',
        is_active=True,
    ).first()

    if shipping_method is None:
        raise ValueError(
            'روش ارسال پست پیشتاز تعریف یا فعال نشده است.'
        )

    return calculate_shipping_cost(
        total_weight_grams=total_weight_grams,
        province=province,
        shipping_method=shipping_method,
        items_total=items_total,
    )
