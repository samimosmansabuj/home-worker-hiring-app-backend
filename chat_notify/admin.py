from django.contrib import admin
from .models import ChatRoom, ChatMessage, Attachment, Notification, ChatEvent
from unfold.admin import ModelAdmin

@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = (
        "id",
        "receiver_name",
        "notification_for",
        "action",
        "is_read",
        "created_at",
    )

    search_fields = (
        "receiver__username",
        "receiver__email",
        "action",
        "message",
    )

    list_filter = (
        "notification_for",
        "is_read",
        "created_at",
        "profile",
    )

    autocomplete_fields = ("receiver",)

    readonly_fields = (
        "notify_text",
        "created_at",
        "entity_type",
        "entity_id",
    )

    date_hierarchy = "created_at"

    fieldsets = (
        ("Recipient Info", {
            "fields": (
                "notification_for",
                "receiver",
                "profile",
            )
        }),

        ("Notification Content", {
            "fields": (
                "action",
                "message",
                "is_read",
            )
        }),

        ("Related Object", {
            "fields": (
                "entity_type",
                "entity_id",
            )
        }),

        ("System Info", {
            "fields": (
                "created_at",
                "notify_text",
            )
        }),
    )

    @admin.display(description="Receiver")
    def receiver_name(self, obj):
        if obj.receiver:
            return f"{obj.receiver.first_name or ''} {obj.receiver.last_name or ''}".strip()
        return "-"



@admin.register(ChatRoom)
class ChatRoomAdmin(ModelAdmin):

    list_display = (
        "room_uuid",
        "customer_name",
        "provider_name",
        "last_message_preview",
        "created_at",
    )

    search_fields = (
        "customer__user__username",
        "provider__user__username",
        "uuid",
    )

    list_filter = ("created_at",)

    readonly_fields = ("uuid", "created_at")

    @admin.display(description="Room UUID")
    def room_uuid(self, obj):
        return obj.uuid

    @admin.display(description="Customer")
    def customer_name(self, obj):
        return obj.customer.user.username

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username

    @admin.display(description="Last Message")
    def last_message_preview(self, obj):
        last_msg = obj.messages.first()
        return last_msg.content[:40] if last_msg else "-"

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0

class ChatEventInline(admin.StackedInline):
    model = ChatEvent
    extra = 0

@admin.register(ChatMessage)
class ChatMessageAdmin(ModelAdmin):

    list_display = (
        "id",
        "room_id",
        "sender",
        "message_type",
        "short_content",
        "is_read",
        "timestamp",
    )

    search_fields = (
        "content",
        "room__uuid",
    )

    list_filter = (
        "sender",
        "message_type",
        "is_read",
        "timestamp",
    )

    readonly_fields = ("timestamp",)

    date_hierarchy = "timestamp"

    ordering = ("-timestamp",)

    inlines = [
        AttachmentInline,
        ChatEventInline,
    ]

    fieldsets = (
        ("Message", {
            "fields": (
                "room",
                "sender",
                "message_type",
                "content",
            )
        }),

        ("Status", {
            "fields": (
                "is_read",
                "timestamp",
            )
        }),
    )

    def room_id(self, obj):
        return obj.room.uuid

    def short_content(self, obj):
        return obj.content[:60]
