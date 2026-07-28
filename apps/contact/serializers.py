from rest_framework import serializers
from .models import ContactMessage


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = (
            'id', 'message_type', 'full_name', 'phone_number',
            'email', 'subject', 'body', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('متن پیام نمی‌تواند خالی باشد.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        is_authenticated = bool(request and request.user.is_authenticated)
        if not is_authenticated and not attrs.get('phone_number') and not attrs.get('email'):
            raise serializers.ValidationError('برای پیگیری پاسخ، وارد کردن شماره تلفن یا ایمیل الزامی است.')

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        if user:
            validated_data.setdefault('full_name', user.full_name)
            validated_data.setdefault('phone_number', user.phone_number)
            if user.email:
                validated_data.setdefault('email', user.email)
        return ContactMessage.objects.create(user=user, **validated_data)
