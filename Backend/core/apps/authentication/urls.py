from .views import *
from django.urls import path

urlpatterns = [
    path('register/', RegisterView.as_view(), name="register"),
    path('login/', LoginAPIView.as_view(), name="login"),
    path('logout/', LogoutAPIView.as_view(), name="logout"),
    path('update-infos/', UpdateInfosView.as_view(), name='update_infos'),
    path('update-password/', UpdatePasswordView.as_view(), name='update_password'),
    path('avatar/', UpdateAvatarView.as_view(), name='avatar'),
    
    path('verify-token/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    # by meriem
    path('users/', UserList.as_view(), name='user_list'),


    # after
    #----------------------------------------------------------------------------#
    # path('friends/', FriendListView.as_view(), name='friend_list'),
    # path('add_friend/<int:friend_id>/', AddFriendAPIView.as_view(), name='add_friend'),
    # path('remove_friend/<int:friend_id>/', RemoveFriendAPIView.as_view(), name='remove_friend'),
    # path('match_history/', MatchHistoryAPIView.as_view(), name='match_history'),
    #----------------------------------------------------------------------------#

]
