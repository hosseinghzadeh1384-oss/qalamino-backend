from django.db.models import Avg, Count, FloatField, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters as drf_filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .filters import ProductFilter
from .models import Brand, Category, Product, ProductLike, ProductRating
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    ProductCommentSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductRatingSerializer,
)


@extend_schema(tags=['Store'], summary='لیست و جزییات دسته بندی محصولات')
class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True, parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


@extend_schema(tags=['Store'], summary='لیست و جزییات برند محصولات')
class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


@extend_schema(tags=['Store'], summary='لیست و جزییات محصولات')
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    اکشن‌های اضافی:
    - POST   /products/{slug}/like/       لایک/آنلایک محصول
    - GET    /products/favorites/         محصولات موردعلاقه کاربر جاری
    - GET/POST /products/{slug}/comments/ مشاهده یا ثبت نظر برای محصول
    - POST   /products/{slug}/rate/       ثبت یا بروزرسانی امتیاز (۱ تا ۵ ستاره)
    """
    queryset = Product.objects.filter(status=Product.Status.PUBLISHED)
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['price', 'created_at', 'likes_count', 'average_rating']
    ordering = ['-created_at']

    def get_queryset(self):
        # از Subquery برای محاسبه‌ی تعداد لایک و میانگین امتیاز استفاده می‌شود تا از تورم داده
        # (fan-out) ناشی از join همزمان چند جدول (likes/ratings/variants) جلوگیری شود.
        likes_subquery = (
            ProductLike.objects.filter(product=OuterRef('pk'))
            .order_by().values('product').annotate(c=Count('id')).values('c')
        )
        ratings_avg_subquery = (
            ProductRating.objects.filter(product=OuterRef('pk'))
            .order_by().values('product').annotate(a=Avg('score')).values('a')
        )
        ratings_count_subquery = (
            ProductRating.objects.filter(product=OuterRef('pk'))
            .order_by().values('product').annotate(c=Count('id')).values('c')
        )

        return (
            Product.objects.filter(status=Product.Status.PUBLISHED)
            .select_related('category', 'brand')
            .prefetch_related('images', 'variants')
            .annotate(
                likes_count=Coalesce(Subquery(likes_subquery, output_field=IntegerField()), 0),
                average_rating=Subquery(ratings_avg_subquery, output_field=FloatField()),
                ratings_count=Coalesce(Subquery(ratings_count_subquery, output_field=IntegerField()), 0),
            )
        )

    def get_serializer_class(self):
        if self.action in ('list', 'favorites'):
            return ProductListSerializer
        return ProductDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request
        if request and request.user.is_authenticated and self.action in ('list', 'favorites'):
            context['liked_product_ids'] = set(
                ProductLike.objects.filter(user=request.user).values_list('product_id', flat=True)
            )
        return context

    @extend_schema(tags=['Store'], summary='لایک/آنلایک محصول (toggle)')
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, slug=None):
        product = self.get_object()
        like, created = ProductLike.objects.get_or_create(user=request.user, product=product)
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        return Response({'liked': liked, 'likes_count': product.likes.count()})

    @extend_schema(tags=['Store'], summary='محصولات موردعلاقه کاربر جاری')
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def favorites(self, request):
        queryset = self.filter_queryset(self.get_queryset()).filter(likes__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=['Store'],
        summary='مشاهده نظرات محصول (GET) یا ثبت نظر جدید (POST)',
        request=ProductCommentSerializer,
        responses={201: ProductCommentSerializer}
    )
    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, slug=None):
        product = self.get_object()

        if request.method == 'POST':
            serializer = ProductCommentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(product=product, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = product.comments.filter(is_approved=True).select_related('user').order_by('-created_at')
        page = self.paginate_queryset(queryset)
        serializer = ProductCommentSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=['Store'],
        summary='ثبت یا بروزرسانی امتیاز محصول (۱ تا ۵ ستاره)',
        request=ProductRatingSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "score": {"type": "integer"},
                    "average_rating": {"type": "number"},
                    "ratings_count": {"type": "integer"},
                }
            }
        }
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def rate(self, request, slug=None):
        product = self.get_object()
        serializer = ProductRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating, _created = ProductRating.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'score': serializer.validated_data['score']},
        )
        avg = product.ratings.aggregate(avg=Avg('score'))['avg']

        return Response({
            'score': rating.score,
            'average_rating': round(avg, 1) if avg is not None else None,
            'ratings_count': product.ratings.count(),
        })
