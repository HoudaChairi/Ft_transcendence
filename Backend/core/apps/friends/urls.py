from django.urls import path
from .views import ManageFriendshipView

urlpatterns = [
    path('friendship/', ManageFriendshipView.as_view(), name='friendship_list'),
    path('friendship/<str:action>/<str:username>/', ManageFriendshipView.as_view(), name='manage_friendship'),
]
