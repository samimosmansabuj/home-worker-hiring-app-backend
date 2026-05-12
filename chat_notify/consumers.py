import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatRoom, Attachment, CustomOffer
from django.core.exceptions import ObjectDoesNotExist
import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from channels.exceptions import DenyConnection
from find_worker_config.model_choice import SendMessageType
from .serializers import ChatMessageSerializer
from find_worker_config.model_choice import UserDefault
import mimetypes

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
    
    async def receive(self, text_data):
        data = json.loads(text_data or {})
        message = (data.get("message") or "").strip()

        type_map = {
            "text": SendMessageType.TEXT,
            "image": SendMessageType.IMAGE,
            "video": SendMessageType.VIDEO,
            "audio": SendMessageType.AUDIO,
            "file": SendMessageType.FILE,
            "offer": SendMessageType.OFFER,
            "delete": "delete"
        }
        message_type = type_map.get((data.get("type") or "text").lower().strip(), SendMessageType.TEXT)

        if message_type == "delete":
            message_id = data.get("message_id")
            room_Id = data.get("roomId")
            if not message_id and not room_Id:
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
            file_path = data.get("file")
            file_name = data.get("file_name")
            print("file_path: ", file_path)

            file = self._abs_url(file_path)
            print("file: ", file)
            

            # print("file: ", file)
            # if file:
            #     header, base64_data = file.split(',', 1)
            #     file = ContentFile(base64.b64decode(base64_data), name=file_name)


            ok = await self.save_message_with_attachment(message, file, message_type)
            if not ok:
                return
            user = ok.get("user")
            photo = ok.get("photo")
            message = ok.get("message")
            attachment = ok.get("attachment")
            payload = {
                'type': 'chat_message',
                "id": message.id,
                "sender": message.sender,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
                "attachments": [
                    {
                        'file': attachment.file,
                        'mime': attachment.mime,
                        'name': attachment.name,
                        'size': attachment.size,
                    }
                ],
                'sender_data': {
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
                "sender": message.sender,
                "message_type": message.message_type,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
                "attachments": [],
                'sender_data': {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "photo": photo,
                    "user": user.role,
                },
            }
        elif message_type == SendMessageType.OFFER:
            order_id = data.get("order_id")
            changes_id = data.get("changes_id")
        
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
    def save_message_with_attachment(self, message, file, message_type):
        user = self.scope['user']
        try:
            room = ChatRoom.objects.get(uuid=self.roomId)
        except ObjectDoesNotExist:
            return False
        
        if not file: False
        # ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/", "pdf/")  # files allowed too, see below
        MAX_FILE_MB = 25
        if file.size > MAX_FILE_MB * 1024 * 1024: return False

        file_mime, _ = mimetypes.guess_type(file.name)
        
        msg = ChatMessage.objects.create(sender=self.profileType, room=room, content=message, message_type=message_type)
        att = Attachment.objects.create(
            message=msg,
            file=file,
            mime=file_mime or "",
            name=getattr(file, "name", ""),
            size=file.size,
        )

        photo = ""
        pic = getattr(user, "photo", None) if user else None
        if pic:
            try:
                photo = pic.url
            except Exception:
                photo = ""
        return {"user": user, "photo": photo, "message": msg, "attachment": att}
    
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
        room = ChatRoom.objects.get(uuid=room_uuid)

        if room.customer.user == room.provider.user:
            return False
        elif profileType.upper() == UserDefault.CUSTOMER and room.customer == user.customer_profile:
            return True
        elif profileType.upper() == UserDefault.PROVIDER and room.provider == user.service_provider_profile:
            return True
        else:
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

