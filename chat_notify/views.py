from rest_framework import viewsets, status, mixins
from .serializers import ChatRoomSerializer, ChatMessageSerializer, MessageAttachmentSerializer, RoomStartSerializer, NotificationSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404, redirect
from account.models import User
from .models import ChatMessage, ChatRoom, Attachment, Notification
from find_worker_config.utils import UpdateModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet


class ChatRoomViewsets(UpdateModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_user(self) -> object:
        return self.request.user
    
    def get_queryset(self) -> object:
        return ChatRoom.objects.filter(Q(customer=self.get_user())|Q(provider=self.get_user())).select_related("customer","provider")
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": False,
                "message": f"Method {request.method} not allowed."
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        return Response(
            {
                "status": False,
                "message": f"Method {request.method} not allowed."
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=False, methods=["post"], url_path="start-chat")
    def start_chat(self, request, *args, **kwargs):
        try:
            serializer = RoomStartSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "room": serializer.data
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

    # @action(detail=True, methods=["post", "get"], url_path="message")
    # def room_message(self, request, *args, **kwargs):
    #     if request.method == "POST":
    #         try:
    #             serializer = ChatMessageSerializer(data=request.data)
    #             serializer.is_valid(raise_exception=True)
    #             serializer.save(room=self.get_object())
    #             return Response(
    #                 {
    #                     "status": True,
    #                     "data": serializer.data
    #                 }, status=status.HTTP_201_CREATED
    #             )
    #         except Exception as e:
    #             return Response(
    #                 {
    #                     "status": False,
    #                     "message": str(e)
    #                 }
    #             )
    #     if request.method == "GET":
    #         messages = ChatMessage.objects.filter(room__uuid=self.get_room_uuid())
    #         return Response(
    #             {
    #                 "status": True,
    #                 "data": ChatMessageSerializer(messages, many=True).data
    #             }, status=status.HTTP_200_OK
    #         )

class ChatRoomMessageViewsets(UpdateModelViewSet):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_room_uuid(self):
        return self.kwargs.get("room_uuid")

    def get_room(self):
        return ChatRoom.objects.get(uuid=self.get_room_uuid())

    def get_queryset(self):
        return ChatMessage.objects.select_related("room").filter(room__uuid=self.get_room_uuid())
    
    def perform_create(self, serializer):
        return serializer.save(room=self.get_room())


class NotificationViewsets(UpdateModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    delete_message = "Notification Deleted."

    def get_queryset(self):
        return Notification.objects.filter(received=self.request.user)
    
    def perform_retrieve(self, serializer):
        serializer.instance.is_read = True
        serializer.instance.save(update_fields={"is_read": True})
        return super().perform_retrieve(serializer)
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": False,
                "message": "Notification direct create not allow."
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        return Response(
            {
                "status": False,
                "message": "Notification direct create not allow."
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
