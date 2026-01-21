from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewsets, ChatRoomMessageViewsets, NotificationViewsets
from rest_framework_nested.routers import NestedDefaultRouter

router = DefaultRouter()
router.register(r"room", ChatRoomViewsets, basename="chat-room")
router.register(r"notifications", NotificationViewsets, basename="notifications")

room_router = NestedDefaultRouter(router, r"room", lookup="room")
room_router.register(r"message", ChatRoomMessageViewsets, basename="chat-room-message")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(room_router.urls))
]