from django.urls import path
from .views import (
    GatewayRedirectView,
    PaymentCreateAPIView,
    PaymentVerifyAPIView,
    SepehrCallbackAPIView,
    SizpayCallbackAPIView,
)

urlpatterns = [
    path("create/", PaymentCreateAPIView.as_view(), name="payment-create"),
    path("verify/", PaymentVerifyAPIView.as_view(), name="payment-verify"),

    # صفحه‌ی واسط auto-submit برای درگاه‌هایی که نیاز به POST خودکار دارند (سیزپی/سپهر)
    path("redirect/<str:gateway>/<uuid:payment_id>/", GatewayRedirectView.as_view(), name="payment-gateway-redirect"),

    # آدرس‌های بازگشتی (Callback/ReturnURL) هر درگاه؛ این آدرس‌ها باید همان‌هایی
    # باشند که در تنظیمات (SIZPAY_CALLBACK_URL, SEPEHR_CALLBACK_URL) و/یا پنل
    # هر درگاه ثبت شده‌اند.
    path("callback/sizpay/", SizpayCallbackAPIView.as_view(), name="payment-callback-sizpay"),
    path("callback/sepehr/", SepehrCallbackAPIView.as_view(), name="payment-callback-sepehr"),
]
