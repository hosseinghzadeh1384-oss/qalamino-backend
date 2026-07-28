from rest_framework import serializers
from .models import NewsletterSubscriber


class NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]

    def validate_email(self, value):
        value = value.lower()

        if NewsletterSubscriber.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً در خبرنامه ثبت شده است.")

        return value
