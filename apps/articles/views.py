from django.db.models import F, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters as drf_filters, generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .filters import ArticleFilter
from .models import Article, ArticleCategory, ArticleLike, Comment, Tag
from .serializers import (
    ArticleCategorySerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    TagSerializer,
)


def visible_articles_queryset():
    """مقالات منتشرشده‌ای که تاریخ انتشارشان رسیده (پشتیبانی از انتشار زمان‌بندی‌شده)"""
    return Article.objects.filter(
        status=Article.Status.PUBLISHED, published_at__lte=timezone.now()
    ).select_related('category', 'author').prefetch_related('tags', 'related_products__images')


@extend_schema(tags=['Articles'], summary='نمایش دسته بندی مقالات و مشاهده جزییات بر اساس اسلاگ')
class ArticleCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ArticleCategory.objects.filter(is_active=True)
    serializer_class = ArticleCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


@extend_schema(tags=['Articles'], summary='نمایش تگ های مقالات و مشاهده جزییات بر اساس اسلاگ')
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


@extend_schema(tags=['Articles'], summary='نمایش لیست و جزییات مقالات')
class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = visible_articles_queryset()
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = ArticleFilter
    search_fields = ['title', 'excerpt', 'content']
    ordering_fields = ['published_at', 'views_count']
    ordering = ['-published_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Article.objects.filter(pk=instance.pk).update(views_count=F('views_count') + 1)
        instance.refresh_from_db(fields=['views_count'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@extend_schema(
    tags=['Articles'],
    summary='لیست نظرات تاییدشده‌ی یک مقاله + ثبت نظر جدید',
    request=CommentCreateSerializer,
    responses={201: CommentSerializer}
)
class ArticleCommentListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

    def get_article(self):
        if not hasattr(self, '_article'):
            self._article = generics.get_object_or_404(visible_articles_queryset(), slug=self.kwargs['slug'])
        return self._article

    def get_queryset(self):
        article = self.get_article()
        qs = article.comments.filter(parent__isnull=True).select_related('user')
        if self.request.user.is_authenticated:
            # کاربر نظرات تاییدنشده‌ی خودش را هم می‌بیند، بقیه فقط نظرات تاییدشده را
            qs = qs.filter(Q(is_approved=True) | Q(user=self.request.user))
        else:
            qs = qs.filter(is_approved=True)
        return qs

    def perform_create(self, serializer):
        article = self.get_article()
        serializer.save(article=article, user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            context['article'] = self.get_article()
        return context

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = {
            **response.data,
            'detail': 'نظر شما ثبت شد و پس از تایید ادمین نمایش داده می‌شود.',
        }
        return response


@extend_schema(tags=['Articles'], summary='حذف نظر (فقط توسط نویسنده‌ی همان نظر یا ادمین)')
class CommentDeleteView(generics.DestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Comment.objects.all()
        return Comment.objects.filter(user=self.request.user)


@extend_schema(tags=['Articles'], summary='لایک / آنلایک کردن یک مقاله')
class ArticleLikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, *args, **kwargs):
        article = generics.get_object_or_404(visible_articles_queryset(), slug=slug)
        like, created = ArticleLike.objects.get_or_create(article=article, user=request.user)

        if not created:
            like.delete()
            liked = False
        else:
            liked = True

        return Response(
            {'liked': liked, 'likes_count': article.likes.count()},
            status=status.HTTP_200_OK,
        )
