from rest_framework import serializers
from .models import Ticket, TicketReply, TicketSenderType, SignUpSlider, CustomerScreenSlide
from find_worker_config.model_choice import UserRole
from task.models import AdminWallet, PaymentTransaction


# -------------------
# Ticket Reply Serializer
class TicketReplySerializer(serializers.ModelSerializer):
    reply_sender_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TicketReply
        fields = ["id", "reply_sender", "reply_sender_name", "sender_type", "message", "attachment", "created_at"]
        read_only_fields = ["id", "reply_sender", "reply_sender_name", "sender_type", "created_at"]

    def get_reply_sender_name(self, obj):
        return obj.reply_sender.username if obj.reply_sender else None

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        sender_type = request.headers.get("sender-type", "")
        if not sender_type:
            raise Exception("Sender Type Missing!")
        elif sender_type == TicketSenderType.USER and user.role == UserRole.ADMIN:
            raise Exception("Sender Type & User Role is not same!")
        elif sender_type == TicketSenderType.ADMIN and user.role == UserRole.USER:
            raise Exception("Sender Type & User Role is not same!")
        
        validated_data["reply_sender"] = user
        validated_data["sender_type"] = sender_type
        return super().create(validated_data)
# -------------------

# -------------------
# Ticket Serializer
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

# -------------------
# Ticket Status Update Serializer
class TicketStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["status"]
# -------------------




# -------------------
# Admin Wallet Serializer
class AdminWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminWallet
        fields = ["current_balance", "payment_balance", "hold_balance", "total_withdraw"]
# -------------------

# -------------------
# Singup Slider Serializer
class SignUpSliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUpSlider
        fields = "__all__"
# -------------------

# -------------------
# Customer Screen Slider Serializer
class CustomerScreenSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerScreenSlide
        fields = "__all__"
# -------------------


