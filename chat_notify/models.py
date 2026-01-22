from django.db import models
from account.models import User
# from task.models import ServiceTask
from find_worker_config.model_choice import SendMessageType, CustomOfferStatus, NotifyType
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class ChatRoom(models.Model):
    uuid = models.CharField(max_length=255, blank=True, null=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_customer")
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_provider")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4().hex
        return super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ('customer', 'provider')
    
    def __str__(self):
        return f"ChatRoom: {self.customer.username} & {self.provider.username}"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    type = models.CharField(max_length=16, choices=SendMessageType, default=SendMessageType.TEXT)
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["timestamp"]
    
    def __str__(self):
        return f"{self.sender.email}: {self.content[:20]}"

class Attachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="chat/")
    mime = models.CharField(max_length=100, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    size = models.BigIntegerField(default=0)


class Notification(models.Model):
    send = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=50, blank=True, null=True, choices=NotifyType.choices)
    data = models.JSONField(default=dict, blank=True, null=True)
    is_read = models.BooleanField(default=False)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    service = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)

