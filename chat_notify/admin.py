from django.contrib import admin
from .models import ChatRoom, ChatMessage, Attachment, Notification

admin.site.register(ChatRoom)
admin.site.register(ChatMessage)
admin.site.register(Attachment)
admin.site.register(Notification)
