from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from .models import OTPCode
from .serializers import LogoutSerializer, OTPRequestSerializer, OTPVerifySerializer, UserProfileSerializer
from .sms import SMSProviderError, get_sms_provider


@extend_schema(
    tags=['Auth'],
    summary='درخواست ارسال کد OTP به شماره تلفن',
    request=OTPRequestSerializer,
    responses={200: None}
)
class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'otp'

    def post(self, request, *args, **kwargs):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        last_otp = OTPCode.get_latest_active(phone_number)

        if last_otp and not last_otp.is_expired:
            wait_seconds = settings.OTP_RESEND_COOLDOWN_SECONDS - int(
                (timezone.now() - last_otp.created_at).total_seconds()
            )
            if wait_seconds > 0:
                return Response(
                    {'detail': f'لطفاً {wait_seconds} ثانیه دیگر دوباره تلاش کنید.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        otp, raw_code = OTPCode.generate_for(phone_number)

        try:
            get_sms_provider().send_otp(phone_number, raw_code)
        except SMSProviderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                'detail': 'کد تایید ارسال شد.',
                'expires_in': settings.OTP_EXPIRY_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['Auth'],
    summary='تایید کد OTP و دریافت JWT (ورود یا ثبت‌نام خودکار)',
    request=OTPVerifySerializer,
)
class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'otp'

    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


@extend_schema(tags=['Auth'], summary='تمدید access token')
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


@extend_schema(
    tags=['Auth'],
    summary='خروج از حساب (بلک‌لیست کردن refresh token)',
    request=LogoutSerializer,
    responses={205: None},
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_205_RESET_CONTENT)


@extend_schema(tags=['Auth'], summary='دریافت / ویرایش پروفایل کاربر جاری')
class ProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
