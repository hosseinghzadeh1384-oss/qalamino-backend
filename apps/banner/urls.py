from rest_framework.routers import DefaultRouter
from .views import BannerViewSet

app_name = 'banner'

router = DefaultRouter()
router.register('banners', BannerViewSet, basename='banner')

urlpatterns = router.urls
