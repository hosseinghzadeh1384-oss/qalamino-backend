from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import OTPCode, phone_regex

User = get_user_model()


class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex])

    def validate_phone_number(self, value):
        return value.strip()


class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(validators=[phone_regex])
    code = serializers.CharField(min_length=settings.OTP_CODE_LENGTH, max_length=settings.OTP_CODE_LENGTH)

    def validate(self, attrs):
        phone_number = attrs['phone_number'].strip()
        code = attrs['code'].strip()

        otp = OTPCode.get_latest_active(phone_number)
        if not otp:
            raise serializers.ValidationError({'code': 'کدی برای این شماره یافت نشد. ابتدا درخواست کد دهید.'})

        if otp.is_expired:
            raise serializers.ValidationError({'code': 'کد منقضی شده است. دوباره درخواست دهید.'})

        if otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            raise serializers.ValidationError({'code': 'تعداد تلاش‌های مجاز تمام شده. کد جدید درخواست دهید.'})

        if not otp.check_code(code):
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            remaining = max(settings.OTP_MAX_VERIFY_ATTEMPTS - otp.attempts, 0)
            raise serializers.ValidationError({'code': f'کد نادرست است. {remaining} تلاش باقی مانده است.'})

        otp.is_used = True
        otp.save(update_fields=['is_used'])

        self.otp = otp
        attrs['phone_number'] = phone_number
        return attrs

    def save(self, **kwargs):
        phone_number = self.validated_data['phone_number']
        user = User.objects.filter(phone_number=phone_number).first()
        created = False

        if user is None:
            user = User.objects.create_user(phone_number=phone_number, is_phone_verified=True)
            created = True
        elif not user.is_phone_verified:
            user.is_phone_verified = True
            user.save(update_fields=['is_phone_verified'])

        refresh = RefreshToken.for_user(user)
        refresh['phone_number'] = user.phone_number
        refresh['full_name'] = user.full_name

        return {
            'user': {
                'id': user.id,
                'phone_number': user.phone_number,
                'full_name': user.full_name,
                'is_new_user': created,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except Exception as exc:
            raise serializers.ValidationError({'refresh': 'توکن نامعتبر یا منقضی شده است.'}) from exc


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'phone_number', 'full_name', 'email', 'is_phone_verified', 'date_joined')
        read_only_fields = ('id', 'phone_number', 'is_phone_verified', 'date_joined')
