from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ChatRoom, ChatMessage, ChatEvent
from .serializers import ChatMessageSpecialSerializer
from copy import deepcopy

def push_notification(user_id, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notify_{user_id}",
        {
            "type": "notify",
            "data": data
        }
    )

def push_notify_role(role, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"role_{role}",
        {
            "type": "notify",
            "data": data
        }
    )

def push_notify_all(data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notify_all",
        {
            "type": "notify",
            "data": data
        }
    )


class PushSendMessage:
    def __init__(self, request, room):
        self.request = request
        self.room = room
        self.payload = None
    
    def get_payload(self, message, order=None, attachment=None):
        payload = ChatMessageSpecialSerializer(message).data
        payload["type"] = "chat_message"
        # payload = {
        #     "type": 'chat_message',
        #     "id": message.id,
        #     "message_type": message.message_type,
        #     "content": message.content,
        #     "timestamp": message.timestamp.isoformat(),
        #     "is_read": message.is_read,
            
        #     "attachments": [],
        #     "event": [],
            
        #     "sender": message.sender,
        #     "sender_data": {
        #         "first_name": self.request.user.first_name,
        #         "last_name": self.request.user.last_name,
        #         "photo": self.request.user.photo if self.request.user.photo else None,
        #         "user": self.request.user.role,
        #     },
        # }
        # if order:
        #     payload["event"] = message.event.payload
        # if attachment:
        #     payload["attachments"] = str(attachment)
        return payload
    
    def get_event_payload(self, message):
        payload = ChatMessageSpecialSerializer(message).data
        event_payload = deepcopy(payload["event"])
        event_payload.pop("payload", None)
        return event_payload
    
    def order_chat_message(self, sender, order, message_type, event_type, changes_object=None):
        msg = ChatMessage.objects.create(
            room=self.room, sender=sender, message_type=message_type
        )
        msg_event = ChatEvent.objects.create(
            message=msg, order_object=order, reference_object=changes_object, event_type=event_type
        )
        
        event_payload = self.get_event_payload(msg)
        msg_event.payload = event_payload
        msg_event.save()
        
        self.payload = self.get_payload(message=msg, order=order)
        return msg
    
    def sendWithAttachment(self):
        pass
    
    def send_message(self):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{self.room.uuid}",
            self.payload
        )

