from .views import *
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login/', LoginAPIView.as_view(), name="login"),
    # path('logout/', LogoutAPIView.as_view(), name="logout"),
    path('update-name/', UpdateDisplayNameView.as_view(), name='update-name'),
    
    path('verify-token/', TokenVerifyView.as_view(), name='token_verify'),
    path('refresh-token/', TokenRefreshView.as_view(), name='token_refresh'),

    # by meriem
    path('users/', UserList.as_view(), name='user_list'),


    # after
    #----------------------------------------------------------------------------#
    # path('update/', UpdateProfileView.as_view(), name='update_profile'),
    # path('friends/', FriendListView.as_view(), name='friend_list'),
    # path('add_friend/<int:friend_id>/', AddFriendAPIView.as_view(), name='add_friend'),
    # path('remove_friend/<int:friend_id>/', RemoveFriendAPIView.as_view(), name='remove_friend'),
    # path('match_history/', MatchHistoryAPIView.as_view(), name='match_history'),
    #----------------------------------------------------------------------------#
    # path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
