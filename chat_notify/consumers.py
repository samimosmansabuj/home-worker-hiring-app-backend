import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatRoom, Attachment
from django.core.exceptions import ObjectDoesNotExist
import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from channels.exceptions import DenyConnection
from find_worker_config.model_choice import SendMessageType
from .serializers import ChatMessageSerializer
from find_worker_config.model_choice import UserDefault

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        self.roomId = self.scope['url_route']['kwargs']['roomId']
        self.profileType = self.scope['url_route']['kwargs']['profileType'].upper()

        if self.profileType not in UserDefault.values:
            await self.close()
            return
        if not user.is_authenticated:
            raise DenyConnection("Unauthorized")
        if await self.verify_room_id(self.roomId) is False:
            await self.close()
            return
        if  await self.check_user_and_room(user, self.profileType, self.roomId) is False:
            await self.close()
            return
        self.room_group_name = f'chat_{self.roomId}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    def send(self, text_data = None, bytes_data = None, close = False):
        return super().send(text_data, bytes_data, close)
    
    async def receive(self, text_data):
        data = json.loads(text_data or "{}")
        message = (data.get("message") or "").strip()

        type_map = {
            "text": SendMessageType.TEXT,
            "image": SendMessageType.IMAGE,
            "video": SendMessageType.VIDEO,
            "audio": SendMessageType.AUDIO,
            "file": SendMessageType.FILE,
            # "offer": SendMessageType.OFFER,
            "delete": "delete"
        }
        message_type = type_map.get((data.get("type") or "text").lower().strip(), SendMessageType.TEXT)

        if message_type == "delete":
            message_id = data.get("message_id")
            room_Id = data.get("roomId")
            if not message_id or not room_Id:
                return
            
            ok = await self.delete_message(message_id, room_Id)
            if not ok:
                return
            payload = {
                'type': 'chat_message',
                'message_type': "delete",
                'message_id': message_id
            }
        elif message_type in [SendMessageType.IMAGE, SendMessageType.VIDEO, SendMessageType.AUDIO, SendMessageType.FILE]:
            # {url, mime, name, size}
            attachment_size = data.get("attachment_size")
            attachment_name = data.get("attachment_name", "uploaded_image.png")
            raw_file = data.get("raw_file")
            
            if raw_file:
                header, base64_data = raw_file.split(',', 1)
                file = ContentFile(base64.b64decode(base64_data), name=attachment_name)
            
            ok = await self.save_message_with_attachment(message, file, attachment_size, message_type)
            user = ok.get("user")
            photo = ok.get("photo")
            message = ok.get("message")
            attachment = ok.get("attachment")
            
            payload = {
                "type": 'chat_message',
                
                "id": message.id,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
                
                'attachments': {
                    'url': self._abs_url(attachment.file.url),
                    'mime': attachment.file.mime or "",
                    'name': attachment.file.name or "",
                    'size': attachment.size or 0,
                },
                "event": {},
                
                "sender": message.sender,
                "sender_data": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "photo": photo,
                    "user": user.role,
                },
            }
        elif message_type == SendMessageType.TEXT:
            if not message:
                return
            ok = await self.save_message(message, message_type)
            if not ok:
                return
            user = ok.get("user")
            photo = ok.get("photo")
            message = ok.get("message")
            payload = {
                "type": 'chat_message',
                
                "id": message.id,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
                
                "attachments": {},
                "event": {},
                
                "sender": message.sender,
                "sender_data": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "photo": photo,
                    "user": user.role,
                },
            }
        
        await self.channel_layer.group_send(
            self.room_group_name, payload
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
    
    # ======================Database Object Update in Websocket Consumer================
    @database_sync_to_async
    def delete_message(self, message_id, room_Id):
        try:
            room = get_object_or_404(ChatRoom, id=room_Id)
            message = get_object_or_404(ChatMessage, id=message_id, room=room)
            message.delete()
            return True
        except ChatMessage.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_message_with_attachment(self, message, file, file_size, msg_type):
        user = self.scope['user']
        try:
            room = ChatRoom.objects.get(uuid=self.roomId)
        except ObjectDoesNotExist:
            return False
        
        if not file:
            return False
        # ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/", "pdf/")  # files allowed too, see below
        MAX_FILE_MB = 25
        
        if file_size > MAX_FILE_MB * 1024 * 1024:
            return False
        msg = ChatMessage.objects.create(sender=self.profileType, room=room, content=message, message_type=msg_type)
        
        att = Attachment.objects.create(
            message=msg,
            file=file,
            mime=msg_type,
            name=getattr(file, "name", ""),
            size=file_size,
        )

        profile_url = ''
        client_user = getattr(user, 'client_user', None)
        pic = getattr(client_user, 'profile_picture', None) if client_user else None
        if pic:
            try:
                profile_url = pic.url
            except Exception:
                profile_url = ''

        # return {'id': user.id, 'username': user.username, 'profile': profile_url, "url": att.file.url, "mime": att.mime, "name": att.name, "size": att.size, 'message_id': msg.pk}
        return {
            "user": user, "photo": profile_url, "message": msg, "attachment": att
        }
    
    @database_sync_to_async
    def save_message(self, message, message_type):
        user = self.scope['user']
        try:
            room = ChatRoom.objects.get(uuid=self.roomId)
        except ObjectDoesNotExist:
            return False
        
        message = ChatMessage.objects.create(sender=self.profileType, room=room, content=message, message_type=message_type)
        
        photo = ''
        pic = getattr(user, 'photo', None) if user else None
        if pic:
            try:
                photo = pic.url
            except Exception:
                photo = ''

        return {'user': user, 'photo': photo, 'message': message}
    
    @database_sync_to_async
    def verify_room_id(self, room_uuid):
        status = ChatRoom.objects.filter(uuid=room_uuid).exists()
        return status
    
    @database_sync_to_async
    def check_user_and_room(self, user, profileType, room_uuid):
        from find_worker_config.model_choice import UserDefault
        try:
            room = ChatRoom.objects.get(uuid=room_uuid)

            if room.customer.user == room.provider.user:
                return False
            elif profileType.upper() == UserDefault.CUSTOMER and room.customer == user.customer_profile:
                return True
            elif profileType.upper() == UserDefault.PROVIDER and room.provider == user.service_provider_profile:
                return True
            else:
                return False
        except ChatRoom.DoesNotExist:
            return False
    # ======================Database Object Update in Websocket Consumer================
    
    def _http_scheme(self) -> str:
        headers = dict(self.scope.get("headers", []))
        xfproto = headers.get(b"x-forwarded-proto")
        if xfproto:
            proto = xfproto.decode("latin1").split(",")[0].strip().lower()
            return "https" if proto == "https" else "http"
        s = (self.scope.get("scheme") or "http").lower()
        if s in ("https", "wss"):
            return "https"
        return "http"

    def _host_with_port(self, scheme: str) -> str:
        """Prefer X-Forwarded-Host > Host > scope.server; drop default ports."""
        headers = dict(self.scope.get("headers", []))
        xfhost = headers.get(b"x-forwarded-host")
        host = (xfhost or headers.get(b"host") or b"").decode("latin1").strip()

        if not host:
            server = self.scope.get("server")  # e.g. ("127.0.0.1", 8000)
            if server:
                h, p = server[0], server[1]
                default = 443 if scheme == "https" else 80
                host = f"{h}:{p}" if (p and p != default) else h
            else:
                host = "localhost"
        return host

    def _abs_url(self, path: str) -> str:
        """Make absolute URL from /media/... using ASGI scope (scheme/host)."""
        if not path:
            return ""
        if isinstance(path, bytes):
            path = path.decode("utf-8", "ignore")
        if path.startswith(("http://", "https://")):
            return path
        scheme = self._http_scheme()
        host = self._host_with_port(scheme)
        if not path.startswith("/"):
            path = "/" + path
        return f"{scheme}://{host}{path}"


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            raise DenyConnection("Unauthorized")
        
        self.user_group = f"notify_{user.id}"
        self.role_group = f"role_{user.role}"
        self.all_group = "notify_all"

        await self.channel_layer.group_add(
            self.user_group, self.channel_name
        )
        await self.channel_layer.group_add(
            self.role_group, self.channel_name
        )
        await self.channel_layer.group_add(
            self.all_group, self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_group, self.channel_name
        )
        await self.channel_layer.group_discard(
            self.role_group, self.channel_name
        )
        await self.channel_layer.group_discard(
            self.all_group, self.channel_name
        )

    async def notify(self, event):
        await self.send(text_data=json.dumps(event["data"]))

