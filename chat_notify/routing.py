from django.urls import re_path
from .consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    re_path(r"^ws/chat/(?P<roomId>[^/]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/notification/$", NotificationConsumer.as_asgi())
]
