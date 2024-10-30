from django.contrib import admin
from django.urls import path, include

# new:
from django.conf import settings
from django.conf.urls.static import static
from core.apps.game.routing import websocket_urlpatterns


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/chat/', include('core.apps.chat.urls')),
    path('api/', include('core.apps.authentication.urls')),
    path('api/auth/', include('core.apps.remote_auth.urls')),
    path('api/manage/', include('core.apps.friends.urls')),
]

# # new for avatar'
# if settings.DEBUG:  # Only serve media files in development mode
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)