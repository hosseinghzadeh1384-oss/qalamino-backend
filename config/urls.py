from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # اپلیکیشن‌ها
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/store/', include('apps.store.urls')),
    path('api/v1/cart/', include('apps.cart.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/payment/', include('apps.payment.urls')),
    path('api/v1/articles/', include('apps.articles.urls')),
    path('api/v1/banners/', include('apps.banner.urls')),
    path('api/v1/contact/', include('apps.contact.urls')),
    path('api/v1/newsletter/', include('apps.newsletter.urls')),

    # مستندات Swagger / OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
