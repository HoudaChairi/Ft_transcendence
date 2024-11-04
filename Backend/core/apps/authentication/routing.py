from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/online_status/(?P<username>[\w.@+-]+)/$', consumers.OnlineStatusConsumer.as_asgi()),
]
