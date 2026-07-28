from rest_framework import serializers
from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    position_display = serializers.CharField(source='get_position_display', read_only=True)

    class Meta:
        model = Banner
        fields = (
            'id', 'image', 'mobile_image',
            'position', 'position_display', 'link_url', 'order',
        )
