import django_filters as filters
from .models import Product, ProductVariant
from django.db.models.functions import Coalesce
from django.db.models import Case, Exists, F, IntegerField, OuterRef, Subquery, Sum, When


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    brand = filters.CharFilter(field_name='brand__slug', lookup_expr='iexact')
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = filters.BooleanFilter(field_name='stock', method='filter_in_stock')
    color = filters.CharFilter(field_name='color', method='filter_color')
    min_rating = filters.NumberFilter(field_name='rating', method='filter_min_rating')

    class Meta:
        model = Product
        fields = ('category', 'brand', 'min_price', 'max_price', 'in_stock', 'color', 'min_rating')

    def filter_in_stock(self, queryset, name, value):
        variant_stock_subquery = (
            ProductVariant.objects.filter(product=OuterRef('pk'), is_active=True)
            .order_by().values('product').annotate(total=Sum('stock')).values('total')
        )
        has_variants_subquery = ProductVariant.objects.filter(product=OuterRef('pk'))

        queryset = queryset.annotate(
            available_stock=Case(
                When(
                    Exists(has_variants_subquery),
                    then=Coalesce(Subquery(variant_stock_subquery, output_field=IntegerField()), 0),
                ),
                default=F('stock'),
                output_field=IntegerField(),
            )
        )
        return queryset.filter(available_stock__gt=0) if value else queryset.filter(available_stock=0)

    def filter_color(self, queryset, name, value):
        return queryset.filter(
            variants__color_name__iexact=value,
            variants__is_active=True,
        ).distinct()

    def filter_min_rating(self, queryset, name, value):
        return queryset.filter(average_rating__gte=value)
