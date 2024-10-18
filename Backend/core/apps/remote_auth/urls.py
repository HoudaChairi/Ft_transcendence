from django.urls import path
from .views import GoogleLoginAPIView, GoogleLoginCallbackAPIView

urlpatterns = [
    path('google/', GoogleLoginAPIView.as_view(), name='google_login'),
    path('google/callback/', GoogleLoginCallbackAPIView.as_view(), name='google_callback'),
]
