from rest_framework import serializers
from .models import Ticket, TicketReply
from account.models import User


# -------------------
# Ticket Reply Serializer
# -------------------
class TicketReplySerializer(serializers.ModelSerializer):
    reply_sender_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TicketReply
        fields = ["id", "ticket", "reply_sender", "reply_sender_name", "sender_type", "message", "attachment", "created_at"]
        read_only_fields = ["id", "reply_sender_name", "created_at"]

    def get_reply_sender_name(self, obj):
        return obj.reply_sender.username if obj.reply_sender else None

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["reply_sender"] = user
        return super().create(validated_data)


# -------------------
# Ticket Serializer
# -------------------
class TicketSerializer(serializers.ModelSerializer):
    replies = TicketReplySerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Ticket
        fields = [
            "id", "user", "user_name", "user_profile_type", "subject", "order",
            "status", "summary", "attachment", "last_message", "last_reply_at",
            "created_at", "updated_at", "replies"
        ]
        read_only_fields = ["id", "last_message", "last_reply_at", "created_at", "updated_at", "replies"]

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)

# -------------------
# Ticket Status Update Serializer
# -------------------
class TicketStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["status"]

