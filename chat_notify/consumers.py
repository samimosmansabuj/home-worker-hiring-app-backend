import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatRoom
from django.core.exceptions import ObjectDoesNotExist
import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from channels.exceptions import DenyConnection
from find_worker_config.model_choice import SendMessageType
from .serializers import ChatMessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        self.roomId = self.scope['url_route']['kwargs']['roomId']
        if not user.is_authenticated:
            raise DenyConnection("Unauthorized")
        if await self.verify_room_id(self.roomId) is False:
            await self.close()
            return
        if  await self.check_user_and_room(user, self.roomId) is False:
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
        msg_type = (data.get("type") or "text").strip()

        if msg_type.startswith("image/"):
            msg_type = SendMessageType.IMAGE
        elif msg_type.startswith("video/"):
            msg_type = SendMessageType.VIDEO
        elif msg_type.startswith("audio/"):
            msg_type = SendMessageType.AUDIO
        elif msg_type.startswith("application/"):
            msg_type = SendMessageType.FILE
        else:
            msg_type = SendMessageType.TEXT
        
        if msg_type == "delete":
            message_id = data.get("message_id")
            room_Id = data.get("roomId")
            if not message_id and not room_Id:
                return
            
            ok = await self.delete_message(message_id, room_Id)
            if not ok:
                return
            payload = {
                'type': 'chat_message',
                'msg_type': "delete",
                'message_id': message_id
            }
        elif msg_type in ("image", "video", "audio", "file"):
            # {url, mime, name, size}
            attachment_size = data.get("attachment_size")
            attachment_name = data.get("attachment_name", "uploaded_image.png")
            raw_file = data.get("raw_file")
            
            if raw_file:
                header, base64_data = raw_file.split(',', 1)
                file = ContentFile(base64.b64decode(base64_data), name=attachment_name)
            
            ok = await self.save_message_with_attachment(message, file, attachment_size, msg_type)
            
            payload = {
                'type': 'chat_message',
                'msg_type': msg_type,
                'message': message,
                'message_id': ok["message_id"],
                'attachment': {
                    'url': self._abs_url(ok['url']),
                    'mime': ok.get('mime', ''),
                    'name': ok.get('name', ''),
                    'size': ok.get('size', 0),
                },
                'sender': ok["username"],
                'sender_id': ok["id"],
                'sender_profile': self._abs_url(ok["profile"]),
            }
        else:
            if not message:
                return
            ok = await self.save_message(message)
            if not ok:
                return
            payload = {
                'type': 'chat_message',
                'msg_type': msg_type,
                'message': message,
                'message_id': ok["message_id"],
                'sender': ok["username"],
                'sender_id': ok["id"],
                'sender_profile': self._abs_url(ok["profile"]),
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
            room = ChatRoom.objects.get(id=self.roomId)
        except ObjectDoesNotExist:
            return False
        
        if not file:
            False
        # ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/", "pdf/")  # files allowed too, see below
        MAX_FILE_MB = 25
        
        if file_size > MAX_FILE_MB * 1024 * 1024:
            return False
        msg = ChatMessage.objects.create(sender=user, room=room, content=message, type=msg_type)
        
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

        return {'id': user.id, 'username': user.username, 'profile': profile_url, "url": att.file.url, "mime": att.mime, "name": att.name, "size": att.size, 'message_id': msg.pk}
    
    @database_sync_to_async
    def save_message(self, message):
        user = self.scope['user']
        try:
            room = ChatRoom.objects.get(uuid=self.roomId)
        except ObjectDoesNotExist:
            return False
        
        message = ChatMessage.objects.create(sender=user, room=room, content=message)
        
        profile_url = ''
        client_user = getattr(user, 'client_user', None)
        pic = getattr(client_user, 'profile_picture', None) if client_user else None
        if pic:
            try:
                profile_url = pic.url
            except Exception:
                profile_url = ''

        return {'id': user.id, 'username': user.username, 'profile': profile_url, 'message_id': message.pk}
    
    @database_sync_to_async
    def verify_room_id(self, room_uuid):
        status = True if ChatRoom.objects.filter(uuid=room_uuid).exists() else False
        return status
    
    @database_sync_to_async
    def check_user_and_room(self, user, room_uuid):
        room = ChatRoom.objects.get(uuid=room_uuid)
        if room.customer == user or room.provider == user:
            return True
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

