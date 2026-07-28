from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.store.serializers import ProductListSerializer
from .models import Article, ArticleCategory, Comment, Tag

User = get_user_model()


class ArticleCategorySerializer(serializers.ModelSerializer):
    articles_count = serializers.IntegerField(source='articles.count', read_only=True)

    class Meta:
        model = ArticleCategory
        fields = ('id', 'name', 'slug', 'description', 'articles_count')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name')


class ArticleListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'category', 'tags', 'author',
            'excerpt', 'featured_image', 'is_featured',
            'reading_time_minutes', 'views_count', 'likes_count', 'comments_count',
            'published_at',
        )

    def get_comments_count(self, obj):
        return obj.comments.filter(is_approved=True).count()


class ArticleDetailSerializer(serializers.ModelSerializer):
    category = ArticleCategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    related_products = ProductListSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'category', 'tags', 'author',
            'excerpt', 'content', 'featured_image',
            'reading_time_minutes', 'views_count', 'likes_count', 'comments_count', 'is_liked',
            'related_products', 'meta_title', 'meta_description',
            'published_at', 'created_at',
        )

    def get_comments_count(self, obj):
        return obj.comments.filter(is_approved=True).count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()


class CommentReplySerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'created_at')


class CommentSerializer(serializers.ModelSerializer):
    user = AuthorSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'parent', 'is_approved', 'created_at', 'replies')
        read_only_fields = ('is_approved',)

    def get_replies(self, obj):
        approved_replies = obj.replies.filter(is_approved=True).select_related('user')
        return CommentReplySerializer(approved_replies, many=True).data


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content', 'parent')

    def validate_parent(self, value):
        article = self.context['article']
        if value and value.article_id != article.id:
            raise serializers.ValidationError('نظر والد متعلق به این مقاله نیست.')
        return value
