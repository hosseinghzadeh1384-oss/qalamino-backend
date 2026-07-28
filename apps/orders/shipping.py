"""
محاسبه‌ی هزینه‌ی ارسال بر اساس پست پیشتاز.

منطق کار:
1. وزن کل مرسوله از روی وزن تک‌تکِ محصولات/تنوع‌های داخل سفارش و تعدادشان جمع زده می‌شود.
   اگر آیتمی تنوع (varient) داشته باشد و برای همان تنوع وزنی ثبت شده باشد، همان وزن استفاده
   می‌شود؛ در غیر این صورت وزنِ خودِ محصول (`Product.weight_grams`) به کار می‌رود. برای
   محصولاتی که وزنشان هم ثبت نشده، از `settings.DEFAULT_PRODUCT_WEIGHT_GRAMS` استفاده می‌شود
   تا محاسبه هیچ‌وقت با وزنِ صفر/نامعلوم انجام نشود.
2. با توجه به وزن کل و استانِ مقصد (تهران در برابر سایر استان‌ها)، هزینه از روی جدول تعرفه‌ی
   `ShippingTariffRow` خوانده می‌شود.
3. اگر `settings.FREE_SHIPPING_THRESHOLD` تنظیم شده و جمع قیمت کالاها به آن برسد، ارسال رایگان می‌شود.

جدول تعرفه (`ShippingTariffRow`) و هزینه‌ی هر کیلوگرم اضافه (`ShippingSettings.extra_cost_per_kg`)
از پنل ادمین قابل مدیریت هستند، پس تغییر/به‌روزرسانیِ تعرفه‌ی رسمی پست پیشتاز نیازی به تغییر کد
یا دیپلوی مجدد ندارد.
"""
import math
from django.conf import settings


def calculate_total_weight_grams(weighted_items):
    """
    وزن کل (گرم) را از روی لیستی از `(weight_grams, quantity)` محاسبه می‌کند.

    `weight_grams` می‌تواند `None` باشد (یعنی برای آن محصول/تنوع وزنی ثبت نشده)؛ در این صورت
    `settings.DEFAULT_PRODUCT_WEIGHT_GRAMS` جایگزین آن می‌شود.
    """
    default_weight = getattr(settings, 'DEFAULT_PRODUCT_WEIGHT_GRAMS', 200)
    total = 0
    for weight_grams, quantity in weighted_items:
        total += (weight_grams or default_weight) * quantity
    return total


def _is_tehran(province):
    tehran_name = getattr(settings, 'PISHTAZ_TEHRAN_PROVINCE_NAME', 'تهران')
    return (province or '').strip() == tehran_name


def calculate_pishtaz_shipping_cost(total_weight_grams, province, items_total=0):
    """
    هزینه‌ی ارسال پیشتاز (تومان) را بر اساس وزن کل مرسوله و استان مقصد برمی‌گرداند.

    - `total_weight_grams`: وزن کل مرسوله به گرم.
    - `province`: نام استان مقصد (مثلاً همان مقدار فیلد `Order.province`).
    - `items_total`: جمع قیمت کالاها (تومان)، فقط برای بررسی آستانه‌ی ارسال رایگان لازم است.
    """
    # وارد کردن اینجا (به‌جای بالای فایل) برای جلوگیری از مشکل import چرخشی هنگام بارگذاری اپ‌ها
    from .models import ShippingSettings, ShippingTariffRow

    free_shipping_threshold = getattr(settings, 'FREE_SHIPPING_THRESHOLD', 0)
    if free_shipping_threshold and items_total >= free_shipping_threshold:
        return 0

    tariff_table = list(
        ShippingTariffRow.objects.order_by('max_weight_grams').values_list(
            'max_weight_grams', 'tehran_price', 'other_price'
        )
    )
    if not tariff_table:
        return 0

    # وزنِ نامعتبر/صفر را هم با کمترین وزنِ پیش‌فرض جایگزین می‌کنیم تا هزینه هیچ‌وقت صفر نشود
    if total_weight_grams <= 0:
        total_weight_grams = getattr(settings, 'DEFAULT_PRODUCT_WEIGHT_GRAMS', 200)

    is_tehran = _is_tehran(province)

    for max_weight_grams, tehran_price, other_price in tariff_table:
        if total_weight_grams <= max_weight_grams:
            return tehran_price if is_tehran else other_price

    # وزن از بیشترین سقف جدول هم بیشتر است: روی هزینه‌ی آخرین ردیف، به ازای هر کیلوگرم
    # اضافه (یا کسری از آن) هزینه‌ی ShippingSettings.extra_cost_per_kg افزوده می‌شود.
    last_max_weight_grams, last_tehran_price, last_other_price = tariff_table[-1]
    extra_weight_grams = total_weight_grams - last_max_weight_grams
    extra_kg_steps = math.ceil(extra_weight_grams / 1000)
    extra_cost = extra_kg_steps * ShippingSettings.get_solo().extra_cost_per_kg

    base_price = last_tehran_price if is_tehran else last_other_price
    return base_price + extra_cost
