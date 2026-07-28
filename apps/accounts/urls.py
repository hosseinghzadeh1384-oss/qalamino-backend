from django.urls import path
from .views import OTPRequestView, OTPVerifyView, RefreshView, LogoutView, ProfileView

app_name = 'accounts'

urlpatterns = [
    path('otp-request/', OTPRequestView.as_view(), name='otp-request'),
    path('otp-verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('token-refresh/', RefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
