from django.urls import path
from .views import GoogleView, GoogleCallbackView, FtView, FtCallbackView

urlpatterns = [
    path('google/', GoogleView.as_view(), name='google_login'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    path('42/login/', FtView.as_view(), name='ft_login'),
    path('42/callback/', FtCallbackView.as_view(), name='ft_callback'),
]
