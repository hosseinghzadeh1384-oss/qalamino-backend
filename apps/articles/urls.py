from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ArticleCategoryViewSet,
    TagViewSet,
    ArticleViewSet,
    ArticleCommentListCreateView,
    CommentDeleteView,
    ArticleLikeToggleView
)

app_name = 'articles'

router = DefaultRouter()
router.register('categories', ArticleCategoryViewSet, basename='article-category')
router.register('tags', TagViewSet, basename='tag')
router.register('', ArticleViewSet, basename='article')

urlpatterns = [
    path('articles/<slug:slug>/comments/', ArticleCommentListCreateView.as_view(), name='article-comments'),
    path('comments/<int:pk>/', CommentDeleteView.as_view(), name='comment-delete'),
    path('articles/<slug:slug>/like/', ArticleLikeToggleView.as_view(), name='article-like'),
]
urlpatterns += router.urls
