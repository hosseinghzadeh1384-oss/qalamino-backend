from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response


def build_result_response(order_number, payment_status, ref_id=None, message=""):
    """
    اگر FRONTEND_ORDER_RESULT_URL تنظیم شده باشد کاربر به آن صفحه (همراه با
    نتیجه‌ی پرداخت در کوئری‌استرینگ) ریدایرکت می‌شود؛ در غیر این صورت پاسخ JSON
    مستقیم بازگردانده می‌شود (مناسب برای تست دستی بدون فرانت‌اند جدا).
    این تابع بین همه‌ی callback‌ های درگاه‌ها (سیزپی، سپهر) مشترک است.
    """
    if settings.FRONTEND_ORDER_RESULT_URL:
        query = f"order_number={order_number}&status={payment_status}"
        if ref_id:
            query += f"&ref_id={ref_id}"
        return redirect(f"{settings.FRONTEND_ORDER_RESULT_URL}?{query}")

    body = {"order_number": order_number, "status": payment_status, "ref_id": ref_id}
    if message:
        body["message"] = message
    http_status = status.HTTP_200_OK if payment_status == "success" else status.HTTP_400_BAD_REQUEST
    return Response(body, status=http_status)
