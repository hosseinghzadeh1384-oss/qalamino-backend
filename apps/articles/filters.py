import django_filters as filters
from .models import Article


class ArticleFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    tag = filters.CharFilter(field_name='tags__slug', lookup_expr='iexact')
    is_featured = filters.BooleanFilter(field_name='is_featured')

    class Meta:
        model = Article
        fields = ('category', 'tag', 'is_featured')
