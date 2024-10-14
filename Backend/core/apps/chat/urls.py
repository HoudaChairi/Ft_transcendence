from django.urls import path
from . import views

urlpatterns = [
    path('room/<str:user1>/<str:user2>/', views.room, name='room'), 
]
