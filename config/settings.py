from datetime import timedelta
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ---------------------------------------------------------------------------
# امنیت (فقط در production، یعنی وقتی DEBUG=False است، فعال می‌شود)
# نکته: اگر سرور پشت Nginx/Cloudflare با HTTPS است، این تنظیمات لازم‌اند.
# اگر پشت ریورس‌پروکسی هستید و ریدایرکت به https توسط خود Nginx انجام می‌شود،
# SECURE_SSL_REDIRECT را در .env روی False بگذارید تا حلقه‌ی ریدایرکت رخ ندهد.
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=60 * 60 * 24 * 30)  # 30 روز
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ---------------------------------------------------------------------------
# اپلیکیشن‌ها
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    'django_ckeditor_5',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.store',
    'apps.cart',
    'apps.orders',
    'apps.payment',
    'apps.articles',
    'apps.banner',
    'apps.contact',
    'apps.newsletter',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# دیتابیس
# ---------------------------------------------------------------------------
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# ---------------------------------------------------------------------------
# اعتبارسنجی رمز عبور
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# بین‌المللی‌سازی
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# فایل‌های استاتیک و مدیا
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:3000'])

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,

    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),

    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.ScopedRateThrottle',
    ),

    'DEFAULT_THROTTLE_RATES': {
        'otp': '5/min',
    },
}

# ---------------------------------------------------------------------------
# SimpleJWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# ---------------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'qalaminoo API - قلمینو',
    'DESCRIPTION': 'مستندات API فروشگاه آنلاین لوازم التحریر قلمینو',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'persistAuthorization': True,
    },
}

CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "underline",
            "strikethrough",
            "|",
            "link",
            "bulletedList",
            "numberedList",
            "|",
            "insertTable",
            "blockQuote",
            "imageUpload",
            "|",
            "undo",
            "redo",
        ],
    },

    "extends": {
        "toolbar": [
            "heading",
            "|",
            "bold",
            "italic",
            "underline",
            "strikethrough",
            "code",
            "|",
            "fontColor",
            "fontBackgroundColor",
            "|",
            "link",
            "bulletedList",
            "numberedList",
            "outdent",
            "indent",
            "|",
            "insertTable",
            "imageUpload",
            "mediaEmbed",
            "blockQuote",
            "horizontalLine",
            "|",
            "undo",
            "redo",
            "sourceEditing",
        ]
    },
}

# ---------------------------------------------------------------------------
# سبد خرید
# ---------------------------------------------------------------------------
# محدودیت زمانی خرید: مدت زمان (دقیقه) اعتبار سبد خرید از آخرین تغییر؛ پس از این مدت آیتم‌های سبد خالی می‌شوند
CART_EXPIRY_MINUTES = env.int('CART_EXPIRY_MINUTES', default=30)

# مهلت پرداخت سفارش (دقیقه): اگر سفارشی بیش از این مدت در وضعیت
# "در انتظار پرداخت" بماند، دستور مدیریتی `cancel_stale_orders` آن را خودکار
# کنسل کرده و موجودیِ محصول/تنوعِ رزروشده را برمی‌گرداند.
# این دستور خودش زمان‌بندی نمی‌شود؛ باید از طریق cron (یا celery beat) هر چند
# دقیقه یک‌بار اجرا شود - به README مراجعه کنید.
ORDER_PENDING_PAYMENT_TIMEOUT_MINUTES = env.int('ORDER_PENDING_PAYMENT_TIMEOUT_MINUTES', default=60)

# اگر بخواهید فرانت‌اند جدا داشته باشید، کاربر پس از پرداخت به این آدرس ریدایرکت می‌شود
# (به همراه کوئری‌پارامترهای order_number, status, ref_id)
# اگر خالی بماند، پاسخ JSON مستقیم از بک‌اند بازگردانده می‌شود.
FRONTEND_ORDER_RESULT_URL = env('FRONTEND_ORDER_RESULT_URL', default='')

# ---------------------------------------------------------------------------
# هزینه ارسال (پست پیشتاز)
# ---------------------------------------------------------------------------
# وزن پیش‌فرض (گرم) برای محصولاتی که فیلد weight_grams آن‌ها خالی مانده - برای اینکه محاسبه‌ی
# هزینه ارسال هیچ‌وقت با وزنِ صفر/نامعلوم انجام نشود.
DEFAULT_PRODUCT_WEIGHT_GRAMS = env.int('DEFAULT_PRODUCT_WEIGHT_GRAMS', default=200)

# جدول تعرفه‌ی پست پیشتاز (هر ردیف => سقف وزن، هزینه تهران، هزینه سایر استان‌ها) و هزینه‌ی هر
# کیلوگرم اضافه پس از بیشترین سقف جدول، دیگر اینجا هاردکد نیستند: از پنل ادمین و از طریق مدل‌های
# `ShippingTariffRow` و `ShippingSettings` (در apps.orders.models) قابل مدیریت‌اند تا تغییر نرخ‌ها
# نیازی به تغییر کد یا دیپلوی مجدد نداشته باشد.

# نام استانی که به‌عنوان «تهران» شناخته می‌شود (برای تفکیک تعرفه‌ی درون‌شهری/استانی از بین‌استانی)
PISHTAZ_TEHRAN_PROVINCE_NAME = 'تهران'

# اگر جمع قیمت کالاهای سفارش (تومان) به این مقدار برسد، ارسال رایگان می‌شود. صفر یعنی غیرفعال.
FREE_SHIPPING_THRESHOLD = env.int('FREE_SHIPPING_THRESHOLD', default=0)

# ---------------------------------------------------------------------------
# احراز هویت OTP (کد یک‌بارمصرف پیامکی) و سرویس پیامک
# ---------------------------------------------------------------------------
OTP_CODE_LENGTH = env.int('OTP_CODE_LENGTH', default=5)
OTP_EXPIRY_SECONDS = env.int('OTP_EXPIRY_SECONDS', default=120)  # مدت اعتبار کد
OTP_RESEND_COOLDOWN_SECONDS = env.int('OTP_RESEND_COOLDOWN_SECONDS', default=60)  # فاصله بین دو درخواست کد
OTP_MAX_VERIFY_ATTEMPTS = env.int('OTP_MAX_VERIFY_ATTEMPTS', default=5)  # حداکثر تلاش غلط برای هر کد

# 'console' (پیش‌فرض، برای توسعه - کد را فقط در لاگ چاپ می‌کند) یا 'kavenegar'
SMS_BACKEND = env('SMS_BACKEND', default='console')
KAVENEGAR_API_KEY = env('KAVENEGAR_API_KEY', default='')
KAVENEGAR_OTP_TEMPLATE = env('KAVENEGAR_OTP_TEMPLATE', default='ghalamino-otp')
# پیامک به مشتری پس از پرداخت موفق سفارش - token=نام گیرنده, token2=شماره سفارش
KAVENEGAR_ORDER_PAID_CUSTOMER_TEMPLATE = env('KAVENEGAR_ORDER_PAID_CUSTOMER_TEMPLATE', default='order1')
# پیامک به مدیر هم‌زمان با پرداخت موفق سفارش - token=شماره سفارش, token2=مبلغ سفارش
KAVENEGAR_ORDER_PAID_ADMIN_TEMPLATE = env('KAVENEGAR_ORDER_PAID_ADMIN_TEMPLATE', default='managerqaem')
# پیامک به مشتری پس از ثبت کد رهگیری پستی توسط ادمین - token=نام گیرنده, token2=کد رهگیری
KAVENEGAR_ORDER_SHIPPED_TEMPLATE = env('KAVENEGAR_ORDER_SHIPPED_TEMPLATE', default='order2')

# تنظیمات مربوط به درگاه پرداخت
# ---------------------------------------------------------------------------
# آدرس پایه‌ی بک‌اند (بدون / انتهایی) - برای ساخت لینک‌های مطلق صفحه‌ی واسط
# درگاه‌هایی مثل سیزپی/سپهر که باید کاربر با POST به صفحه‌ی بانک منتقل شود.
BACKEND_BASE_URL = env("BACKEND_BASE_URL", default="http://localhost:8000")

# --- سیزپی (SizPay) ---
# مقادیر زیر پس از عقد قرارداد از پنل سیزپی دریافت می‌شوند.
SIZPAY_MERCHANT_ID = env.int("SIZPAY_MERCHANT_ID", default=0)
SIZPAY_TERMINAL_ID = env.int("SIZPAY_TERMINAL_ID", default=0)
SIZPAY_KEY = env("SIZPAY_KEY", default="")  # کلید رمزنگاری AES (کلید 1) - Base64
SIZPAY_IV = env("SIZPAY_IV", default="")  # IV رمزنگاری AES (کلید 2) - Base64
SIZPAY_SIGN_KEY = env("SIZPAY_SIGN_KEY", default="")  # کلید امضای الکترونیکی HMAC-SHA256 (متنی)
# باید در پنل سیزپی معتبر ثبت شود و دقیقاً به همین صورت مطلق در ReturnURL ارسال گردد.
SIZPAY_CALLBACK_URL = env("SIZPAY_CALLBACK_URL", default=f"{BACKEND_BASE_URL}/api/v1/payment/callback/sizpay/")

# --- سپهر (بانک صادرات - پرداخت الکترونیک سپهر) ---
# مقادیر زیر پس از عقد قرارداد و ثبت IP سرور از واحد پذیرندگان سپهر دریافت می‌شوند.
SEPEHR_TERMINAL_ID = env.int("SEPEHR_TERMINAL_ID", default=0)
SEPEHR_CALLBACK_URL = env("SEPEHR_CALLBACK_URL", default=f"{BACKEND_BASE_URL}/api/v1/payment/callback/sepehr/")
