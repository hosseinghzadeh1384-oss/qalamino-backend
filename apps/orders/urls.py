from django.urls import path
from .views import OrderListView, OrderCreateView, OrderDetailView, OrderCancelView, ShippingEstimateView

app_name = 'orders'

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('shipping-estimate/', ShippingEstimateView.as_view(), name='shipping-estimate'),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_number>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
