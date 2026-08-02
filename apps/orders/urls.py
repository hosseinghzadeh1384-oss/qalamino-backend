from django.urls import path
from .views import (
    OrderListView,
    OrderCreateView,
    OrderDetailView,
    OrderCancelView,
    ShippingEstimateView,
    SavedAddressListCreateView,
    SavedAddressRetrieveUpdateDestroyView,
    ShippingMethodListView
)

app_name = 'orders'

urlpatterns = [
    path('', OrderListView.as_view(), name='order-list'),
    path('create/', OrderCreateView.as_view(), name='order-create'),
    path('shipping-methods/', ShippingMethodListView.as_view(), name='shipping-method-list'),
    path('shipping-estimate/', ShippingEstimateView.as_view(), name='shipping-estimate'),
    path("saved-addresses/", SavedAddressListCreateView.as_view(), name="saved-address-list"),
    path("saved-addresses/<int:pk>/", SavedAddressRetrieveUpdateDestroyView.as_view(), name="saved-address-detail"),
    path('<str:order_number>/', OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_number>/cancel/', OrderCancelView.as_view(), name='order-cancel'),
]
