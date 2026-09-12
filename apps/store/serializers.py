from rest_framework import serializers
from .models import Brand, Category, Product, ProductComment, ProductImage, ProductRating, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'parent', 'image', 'children')

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True)
        return CategorySerializer(qs, many=True, context=self.context).data


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'name', 'slug', 'logo', 'description')


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_main', 'order')


class ProductVariantSerializer(serializers.ModelSerializer):
    final_price = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    effective_weight_grams = serializers.IntegerField(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = ProductVariant

        fields = (
            'id',
            'color_name',
            'color_code',
            'design_name',
            'display_name',
            'sku',
            'price',
            'discount_price',
            'final_price',
            'stock',
            'weight_grams',
            'effective_weight_grams',
            'image',
            'is_active',
            'is_available',
        )


class ProductCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductComment
        fields = ('id', 'user_name', 'body', 'created_at')
        read_only_fields = ('id', 'user_name', 'created_at')

    def get_user_name(self, obj):
        return obj.user.full_name or "کاربر ناشناس"

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('متن نظر نمی‌تواند خالی باشد.')
        return value


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating
        fields = ('id', 'score', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field='name', read_only=True)
    brand = serializers.SlugRelatedField(slug_field='name', read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    has_variants = serializers.BooleanField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)
    main_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category', 'brand', 'variant_type',
            'price', 'discount_price', 'final_price',
            'main_image', 'is_available', 'has_variants',
            'likes_count', 'average_rating', 'ratings_count', 'is_liked',
        )

    def get_main_image(self, obj):
        main = obj.images.filter(is_main=True).first() or obj.images.first()
        if main:
            request = self.context.get('request')
            url = main.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_average_rating(self, obj):
        avg = getattr(obj, 'average_rating', None)
        return round(avg, 1) if avg is not None else None

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        liked_ids = self.context.get('liked_product_ids')
        if liked_ids is not None:
            return obj.id in liked_ids
        return obj.likes.filter(user=request.user).exists()


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    final_price = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    has_variants = serializers.BooleanField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category', 'brand', 'description', 'sku', 'meta_title', 'meta_description',
            'variant_type', 'price', 'discount_price', 'final_price', 'stock', 'status',
            'weight_grams', 'images', 'variants', 'has_variants', 'is_available', 'created_at',
            'likes_count', 'average_rating', 'ratings_count', 'comments_count',
            'is_liked', 'my_rating',
        )

    def get_average_rating(self, obj):
        avg = getattr(obj, 'average_rating', None)
        return round(avg, 1) if avg is not None else None

    def get_comments_count(self, obj):
        return obj.comments.filter(is_approved=True).count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_my_rating(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        rating = obj.ratings.filter(user=request.user).first()
        return rating.score if rating else None
