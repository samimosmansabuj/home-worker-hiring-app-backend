from django.db import models
from account.models import User
# from task.models import ServiceTask
from find_worker_config.model_choice import SendMessageType, CustomOfferStatus, NotifyType
import uuid
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from account.utils import image_delete_os, previous_image_delete_os

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

    def image_update(self, instance):
        previous_image_delete_os(instance.file, self.file)
    
    def delete(self, *args, **kwargs):
        image_delete_os(self.file)
        return super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if self.pk and Attachment.objects.filter(pk=self.pk).exists():
            instance = Attachment.objects.get(pk=self.pk)
            self.image_update(instance)


class Notification(models.Model):
    received = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True, null=True)
    is_read = models.BooleanField(default=False)

    entity_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    entity_id = models.PositiveIntegerField(blank=True, null=True)
    service = GenericForeignKey('entity_type', 'entity_id')

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def notify_text(self):
        return f"{self.received.first_name} {self.received.last_name if self.received.last_name else ''} {self.action} at {self.created_at}"

    def __str__(self):
        return f"{self.received.first_name} {self.received.last_name if self.received.last_name else ''} {self.action} at {self.created_at}"
    


