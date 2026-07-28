from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from .models import NewsletterSubscriber
from .serializers import NewsletterSerializer


@extend_schema(tags=['newsletter'], summary='عضویت در خبر نامه')
class NewsletterSubscribeView(CreateAPIView):
    permission_classes = [AllowAny]
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "عضویت شما با موفقیت انجام شد."}, status=status.HTTP_201_CREATED)
