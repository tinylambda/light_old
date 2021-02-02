from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/core/state/$', consumers.StateConsumer.as_asgi())
]
