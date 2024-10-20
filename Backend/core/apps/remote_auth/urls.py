from django.urls import path
from .views import GoogleLoginAPIView, GoogleLoginCallbackAPIView, FTLoginAPIView, FTLoginCallbackAPIView

urlpatterns = [
    path('google/', GoogleLoginAPIView.as_view(), name='google_login'),
    path('google/callback/', GoogleLoginCallbackAPIView.as_view(), name='google_callback'),

    path('42/login/', FTLoginAPIView.as_view(), name='ft_login'),
    path('42/callback/', FTLoginCallbackAPIView.as_view(), name='ft_callback'),
]
