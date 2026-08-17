from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response


def build_result_response(
        order_number,
        payment_status,
        ref_id=None,
        message="",
        order_id=None,
):
    """
    نتیجه پرداخت را به فرانت‌اند منتقل می‌کند.

    در پرداخت موفق، اگر FRONTEND_ORDER_RESULT_URL تنظیم شده باشد،
    کاربر به صفحه موفقیت سفارش با order_id منتقل می‌شود.

    مثال:
    https://qalaminoo.ir/payment/success/<ORDER_ID>

    در صورت نبود URL فرانت یا در پرداخت ناموفق،
    پاسخ JSON بازگردانده می‌شود.
    """

    if (
            payment_status == "success"
            and settings.FRONTEND_ORDER_RESULT_URL
            and order_id
    ):
        frontend_url = settings.FRONTEND_ORDER_RESULT_URL.strip()

        # اگر داخل env از <ORDER_ID> استفاده شده باشد
        if "<ORDER_ID>" in frontend_url:
            frontend_url = frontend_url.replace(
                "<ORDER_ID>",
                str(order_id),
            )
        else:
            # در غیر این صورت order_id به انتهای URL اضافه می‌شود
            frontend_url = (
                f"{frontend_url.rstrip('/')}/{order_id}"
            )

        return redirect(frontend_url)

    body = {
        "order_number": order_number,
        "status": payment_status,
        "ref_id": ref_id,
    }

    if message:
        body["message"] = message

    http_status = (
        status.HTTP_200_OK
        if payment_status == "success"
        else status.HTTP_400_BAD_REQUEST
    )

    return Response(body, status=http_status)
