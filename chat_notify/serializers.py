from rest_framework import serializers
from .models import ChatMessage, ChatRoom, Attachment, Notification, CustomOffer
from account.models import ServiceProviderProfile, User
from find_worker_config.model_choice import UserRole, UserDefault, SendMessageType
import os
import mimetypes


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "photo", "role"]

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = "__all__"

class MessageCustomOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomOffer
        # fields = "__all__"
        exclude = ["message"]
        depth = True

class ChatMessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, required=False)
    custom_offers = MessageCustomOfferSerializer(required=False)
    sender_data = serializers.SerializerMethodField()
    sender = serializers.ChoiceField(required=False, choices=UserDefault.choices)
    class Meta:
        model = ChatMessage
        fields = ["id", "sender", "sender_data", "message_type", "content", "timestamp", "is_read", "attachments", "custom_offers"]
    
    def get_sender_data(self, obj):
        user = None
        if obj.sender == UserDefault.CUSTOMER:
            user = obj.room.customer.user
        if obj.sender == UserDefault.PROVIDER:
            user = obj.room.provider.user
        return UserMiniSerializer(user).data if user else None
    
    def get_message_type_from_mime(self, mime: str):
        if not mime:
            return SendMessageType.FILE
        elif mime.startswith("image/"):
            return SendMessageType.IMAGE
        elif mime.startswith("video/"):
            return SendMessageType.VIDEO
        elif mime.startswith("audio/"):
            return SendMessageType.AUDIO
        return SendMessageType.FILE
    
    def create(self, validated_data):
        attachments_files = self.context['request'].FILES.getlist('attachments')
        custom_offers_data = validated_data.pop("custom_offers", {})

        message = ChatMessage.objects.create(**validated_data)
        message_type = SendMessageType.TEXT

        for file in attachments_files:
            mime, _ = mimetypes.guess_type(file.name)
            Attachment.objects.create(
                message=message,
                file=file,
                mime=mime or "",
                name=file.name,
                size=file.size
            )

            message_type = self.get_message_type_from_mime(mime)
        message.message_type = message_type
        message.save(update_fields=["message_type"])
        return message

class ChatRoomSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    class Meta:
        model = ChatRoom
        fields = ["uuid", "other_user", "unread_count", "last_message"]
    
    def get_last_message(self, obj):
        msg = obj.messages.order_by("-timestamp").only("id","content","message_type","timestamp", "is_read").first()
        if not msg: return None
        return {"id": msg.id, "message_type": msg.message_type, "content": msg.content, "timestamp": msg.timestamp}
    
    def get_other_user(self, obj):
        u = self.context["request"].user
        other = obj.provider if obj.customer.user == u else obj.customer
        return UserMiniSerializer(other.user).data
    
    def get_unread_count(self, obj):
        profile = self.context.get("profile")
        unread_message = obj.messages.filter(is_read=False).exclude(sender=profile)
        print("unread_message", unread_message)
        
        if profile == UserDefault.CUSTOMER:
            return obj.messages.filter(is_read=False).exclude(sender=profile).count()

        return obj.messages.filter(is_read=False).exclude(sender=profile).count()

class RoomStartSerializer(serializers.Serializer):
    provider_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        request = self.context["request"]
        me_customer = request.user.customer_profile
        other_provider = ServiceProviderProfile.objects.get(id=attrs["provider_id"])
        if me_customer == other_provider:
            raise Exception("Same user cannot chat each other!")
        self.customer = me_customer
        self.provider = other_provider
        return super().validate(attrs)

    def create(self, validated):
        request = self.context["request"]
        room, created = ChatRoom.objects.get_or_create(
            customer=self.customer,
            provider=self.provider
        )
        return room
    
    def to_representation(self, instance):
        return ChatRoomSerializer(instance, context=self.context).data





class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Notification
        fields = "__all__"

