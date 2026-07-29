from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from .models import ContactMessage
from .serializers import ContactMessageCreateSerializer


@extend_schema(
    tags=['Contact'],
    summary='ارسال پیام تماس با ما (درخواست / انتقاد / پیشنهاد)',
    request=ContactMessageCreateSerializer,
    responses={201: ContactMessageCreateSerializer}
)
class ContactMessageCreateView(CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageCreateSerializer
    permission_classes = [AllowAny]
