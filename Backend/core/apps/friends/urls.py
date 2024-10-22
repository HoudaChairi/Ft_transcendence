from django.urls import path
from .views import FriendshipView

urlpatterns = [
    path('friendships/', FriendshipView.as_view(), name='friendship-list'),  # For GET, POST
    path('friendships/<str:username>/', FriendshipView.as_view(), name='friendship-detail'),  # For PUT, DELETE
]
