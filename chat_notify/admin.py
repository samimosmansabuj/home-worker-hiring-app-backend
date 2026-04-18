from django.contrib import admin
from .models import ChatRoom, ChatMessage, Attachment, Notification
# from unfold.admin import ModelAdmin

# @admin.register(ChatMessage)
# class ChatMessageAdmin(ModelAdmin):
#     list_display = ("room", "sender", "type", "is_read", "timestamp")
#     list_filter = ("type", "is_read")

#     search_fields = ("content",)

#     list_select_related = ("room",)

admin.site.register(ChatRoom)
admin.site.register(ChatMessage)
admin.site.register(Attachment)
admin.site.register(Notification)
