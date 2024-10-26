from django.urls import path
from .views import ManageFriendshipView

urlpatterns = [
    path('friendship/<str:action>/<str:username>/', ManageFriendshipView.as_view(), name='manage_friendship'),
]
