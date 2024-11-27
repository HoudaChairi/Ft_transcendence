from .views import *
from django.urls import path

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name="register"),
    path('login/', LoginAPIView.as_view(), name="login"),
    path('logout/', LogoutAPIView.as_view(), name="logout"),
    path('update-infos/', UpdateInfosView.as_view(), name='update_infos'),
    path('update-password/', UpdatePasswordView.as_view(), name='update_password'),
    path('avatar/', UpdateAvatarView.as_view(), name='avatar'),
    
    path('verify-token/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
    path('users/', UserList.as_view(), name='user_list'),
    path('leader/', LeaderBoard.as_view(), name='LeaderBoard'),
    path('user/<str:username>/', UserInfos.as_view(), name='user-info'),
    # 2FA
    path('enable-2fa/', Enable2FA.as_view(), name='enable_2fa'),
    path('confirm-2fa/', Confirm2FA.as_view(), name='confirm_2fa'),
    path('verify-2fa/', Verify2FA.as_view(), name='verify_2fa'),
    path('disable-2fa/', Disable2FA.as_view(), name='disable-2fa'),
]
