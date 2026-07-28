from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Banner
from .serializers import BannerSerializer


@extend_schema(tags=['Banners'], summary='نمایش بنر به فرانت/اپ')
class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['position']
    pagination_class = None

    def get_queryset(self):
        now = timezone.now()
        return (
            Banner.objects.filter(is_active=True)
            .filter(Q(start_at__isnull=True) | Q(start_at__lte=now))
            .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
            .order_by('position', 'order', '-created_at')
        )
