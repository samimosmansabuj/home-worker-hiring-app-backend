from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage
import json

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.sender = self.scope["user"]

        if self.sender.is_anonymous:
            await self.close()
            return

        self.receiver_id = self.scope["url_route"]["kwargs"]["user_ID"]
        self.room_name = f"chat_{min(self.sender.id, int(self.receiver_id))}_{max(self.sender.id, int(self.receiver_id))}"

        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")

        chat = await self.get_or_create_chat(self.sender.id, self.receiver_id)
        chat_message = await self.save_message(chat, self.sender, message)

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "message": message,
                "sender_id": self.sender.id,
                "created_at": chat_message.created_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # ---------------- DB Methods ----------------

    @database_sync_to_async
    def get_or_create_chat(self, sender_id, receiver_id):
        user1, user2 = sorted([sender_id, int(receiver_id)])
        chat, _ = ChatMessage.objects.get_or_create(sender=self.sender)
        return chat

    @database_sync_to_async
    def save_message(self, chat, sender, message):
        return ChatMessage.objects.create(
            chat=chat,
            sender=sender,
            message=message
        )


