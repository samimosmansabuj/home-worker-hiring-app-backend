from rest_framework import serializers
from .models import ChatMessage, ChatRoom, Attachment, Notification
from account.models import User
from find_worker_config.model_choice import UserRole

class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "role"]

class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = "__all__"

class ChatMessageSerializer(serializers.ModelSerializer):
    attachments = MessageAttachmentSerializer(many=True, required=False)
    sender_user = serializers.SerializerMethodField()
    sender = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = ChatMessage
        fields = ["id", "sender", "type", "content", "timestamp", "is_read", "attachments", "sender_user"]
    
    def get_sender_user(self, obj):
        other = UserMiniSerializer(obj.sender).data
        return other

class ChatRoomSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    class Meta:
        model = ChatRoom
        # fields = "__all__"
        fields = ["uuid", "other_user", "unread_count"]
    
    def get_last_message(self, obj):
        msg = obj.messages.order_by("-timestamp").only("id","content","type","timestamp").first()
        if not msg: return None
        return {"id": msg.id, "type": msg.type, "content": msg.content, "timestamp": msg.timestamp}
    
    def get_other_user(self, obj):
        u = self.context["request"].user
        print("u: ", u.first_name, u.last_name)
        other = obj.provider if obj.customer_id == u.id else obj.customer
        return UserMiniSerializer(other).data
    
    def get_unread_count(self, obj):
        u = self.context["request"].user
        return obj.messages.filter(is_read=False).exclude(sender_id=u.id).count()

class RoomStartSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate(self, attrs):
        request = self.context["request"]
        me = request.user
        other = User.objects.get(id=attrs["user_id"])
        if (me.role and other.role) == UserRole.ADMIN:
            raise Exception("Admin User Can't Start Chat!")
        elif me == other:
            raise Exception("Same user cannot chat each other!")
        self.customer = me
        self.provider = other
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

