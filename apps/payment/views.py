from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .gateways.factory import PaymentGatewayFactory
from .models import Payment, PaymentStatus
from .permissions import IsAuthenticatedUser
from .services import PaymentService, PaymentServiceError
from .utils import build_result_response
from .serializers import (
    PaymentCreateSerializer,
    PaymentVerifySerializer,
    SepehrCallbackSerializer,
    SizpayCallbackSerializer,
)


@extend_schema(
    tags=['Payment'],
    summary="ایجاد پرداخت جدید",
    request=PaymentCreateSerializer,
    responses={
        201: {
            "type": "object",
            "properties": {
                "payment_id": {"type": "string", "format": "uuid"},
                "authority": {"type": "string"},
                "payment_url": {"type": "string"},
                "status": {"type": "string"},
            }
        }
    }
)
class PaymentCreateAPIView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        serializer = PaymentCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()

        try:
            payment = PaymentService.create_payment_request(payment)
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "payment_id": payment.id,
                "authority": payment.authority,
                "payment_url": payment.payment_url,
                "status": payment.status,
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=['Payment'],
    summary="برای verify دستی",
    request=PaymentVerifySerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "payment_id": {"type": "integer"},
                "status": {"type": "string"},
                "ref_id": {"type": "string"},
            }
        }
    }
)
class PaymentVerifyAPIView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.payment

        try:
            payment = PaymentService.verify_payment(payment)
        except PaymentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "payment_id": payment.id,
                "status": payment.status,
                "ref_id": payment.ref_id,
            },
            status=status.HTTP_200_OK
        )


class GatewayRedirectView(View):
    """
    صفحه‌ی واسط برای درگاه‌هایی مثل سیزپی و سپهر که نیازمند POST خودکار چند
    فیلدی به صفحه‌ی پرداخت بانک هستند (به‌جای یک لینک ساده‌ی GET).

    ``payment_url`` بازگشتی این دو درگاه از ``create_payment`` به همین ویو اشاره
    می‌کند؛ کاربر یک لحظه این صفحه را می‌بیند و مرورگرش خودکار فرم را submit می‌کند.
    این یک View ساده‌ی جنگو است (نه DRF)، چون خروجی آن HTML است نه JSON.
    """

    def get(self, request, gateway, payment_id):
        payment = get_object_or_404(Payment, id=payment_id, gateway=gateway)

        if not payment.authority or payment.status != PaymentStatus.PENDING:
            raise Http404("این تراکنش قابل پرداخت نیست.")

        gw = PaymentGatewayFactory.get_gateway(payment.gateway)
        if not hasattr(gw, "build_redirect_form"):
            raise Http404("این درگاه نیازی به صفحه‌ی واسط ندارد.")

        action_url, fields = gw.build_redirect_form(payment)

        return render(
            request,
            "payment/gateway_redirect.html",
            {"action_url": action_url, "fields": fields},
        )


@extend_schema(tags=['Payment'], request=SizpayCallbackSerializer)
class SizpayCallbackAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return self._handle(request.query_params)

    def post(self, request):
        return self._handle(request.data)

    def _handle(self, data):
        serializer = SizpayCallbackSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        payment = serializer.payment
        order_number = payment.order.order_number
        rescod = str(serializer.validated_data.get("ResCod"))

        if rescod not in ("0", "00"):
            PaymentService.mark_failed(payment)
            message = serializer.validated_data.get("Message") or "پرداخت توسط کاربر لغو یا ناموفق بود."
            return build_result_response(order_number, "failed", message=message)

        try:
            payment = PaymentService.verify_payment(payment)
        except PaymentServiceError as exc:
            return build_result_response(order_number, "failed", message=str(exc))

        payment_status = "success" if payment.status == "success" else "failed"
        return build_result_response(order_number, payment_status, ref_id=payment.ref_id)


@extend_schema(tags=['Payment'], request=SepehrCallbackSerializer)
class SepehrCallbackAPIView(APIView):
    """
    آدرس بازگشتی (callbackURL) که سپهر پس از پرداخت کاربر را به آن هدایت می‌کند.
    سپهر توکن را در callback برنمی‌گرداند، بنابراین Payment از روی invoiceid
    (شماره سفارش) پیدا می‌شود و «رسید دیجیتال» برای مرحله‌ی Advice ذخیره می‌شود.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return self._handle(request.query_params)

    def post(self, request):
        return self._handle(request.data)

    def _handle(self, data):
        serializer = SepehrCallbackSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        payment = serializer.payment
        order_number = payment.order.order_number
        validated = serializer.validated_data

        # داده‌های لازم برای مرحله‌ی Advice (تایید تراکنش) را روی پرداخت ذخیره می‌کنیم
        payment.extra_data = {
            **(payment.extra_data or {}),
            "digitalreceipt": validated.get("digitalreceipt", ""),
            "cardnumber": validated.get("cardnumber", ""),
            "rrn": validated.get("rrn", ""),
            "tracenumber": validated.get("tracenumber", ""),
        }
        payment.save(update_fields=["extra_data", "updated_at"])

        respcode = str(validated.get("respcode"))
        if respcode != "0":
            PaymentService.mark_failed(payment)
            message = validated.get("respmsg") or "پرداخت توسط کاربر لغو یا ناموفق بود."
            return build_result_response(order_number, "failed", message=message)

        try:
            payment = PaymentService.verify_payment(payment)
        except PaymentServiceError as exc:
            return build_result_response(order_number, "failed", message=str(exc))

        payment_status = "success" if payment.status == "success" else "failed"
        return build_result_response(order_number, payment_status, ref_id=payment.ref_id)
