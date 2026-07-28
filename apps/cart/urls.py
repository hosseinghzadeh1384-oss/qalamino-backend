from django.urls import path
from .views import CartDetailView, CartItemAddView, CartItemUpdateView, CartItemRemoveView, CartClearView

app_name = 'cart'

urlpatterns = [
    path('', CartDetailView.as_view(), name='cart-detail'),
    path('add-items/', CartItemAddView.as_view(), name='cart-item-add'),
    path('items/<int:item_id>/', CartItemUpdateView.as_view(), name='cart-item-update'),
    path('items/<int:item_id>/remove/', CartItemRemoveView.as_view(), name='cart-item-remove'),
    path('clear/', CartClearView.as_view(), name='cart-clear'),
]
