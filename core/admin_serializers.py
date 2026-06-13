from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import ValidationError
from find_worker_config.model_choice import UserDefault,UserRole, UserStatus, OrderPaymentStatus, RefundStatus
from account.models import User, CustomerProfile, ServiceProviderProfile, Address
from task.models import Order, OrderAttachment, PaymentTransaction, OrderRefundRequest, OrderChangesRequest
from django.utils import timezone


class AdminLoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        if self.user.role != UserRole.ADMIN:
            raise serializers.ValidationError(
                {"detail": "You are not authorized as admin."}
            )
        return data

class AdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "password",]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create(
            **validated_data,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_active=True
        )
        user.set_password(password)
        user.save()
        return user

class AdminProviderSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    complete_total = serializers.SerializerMethodField()
    rating = serializers.FloatField(read_only=True)

    last_active = serializers.DateTimeField(source="user.last_login", read_only=True)

    location = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProviderProfile
        fields = ["id", "first_name", "last_name", "email", "phone", "complete_total", "rating", "last_active", "location"]

    def get_complete_total(self, obj):
        return obj.total_jobs

    def get_location(self, obj):
        if obj.office_location:
            return {
                "id": obj.office_location.id,
                "title": str(obj.office_location)
            }
        return None

class AdminCustomerSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    complete_total = serializers.SerializerMethodField()
    cancelled_total = serializers.SerializerMethodField()

    location = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = ["id", "first_name", "last_name", "email", "phone", "total_orders", "complete_total", "cancelled_total", "location"]

    def get_complete_total(self, obj):
        return obj.completed_orders if hasattr(obj, "completed_orders") else 0

    def get_cancelled_total(self, obj):
        return obj.cancelled_orders if hasattr(obj, "cancelled_orders") else 0

    def get_user_profile_address(self, user):
        address_objects = Address.objects.filter(
            user=user, is_default=True
        )
        if address_objects:
            address = address_objects.first()
        elif Address.objects.filter(user=user).exists():
            address = Address.objects.filter(user=user).first()
        
        if address:
            return {
                "id": address.id,
                "display_address": f"{address.address_line} {address.city}",
                "lat": address.lat,
                "lng": address.lng
            }
        else:
            return None
    
    def get_location(self, obj):
        return self.get_user_profile_address(obj.user)

# ===================Order=======================
class AdminOrderSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="id", read_only=True)
    date = serializers.DateTimeField(source="created_at", read_only=True)
    customer = serializers.SerializerMethodField()
    provider = serializers.SerializerMethodField()
    status_duration = serializers.SerializerMethodField()

    payment = serializers.CharField(source="payment_status", read_only=True)
    payment_type = serializers.SerializerMethodField()
    budget = serializers.DecimalField(source="amount", max_digits=10, decimal_places=2, read_only=True)
    working_start_time = serializers.TimeField(
        input_formats=["%I:%M %p", "%H:%M"]
    )
    action = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "title", "order_id", "date", "customer", "payment", "payment_type", "provider", "status", "status_duration", "budget", "working_start_time", "action"]

    def get_customer(self, obj):
        if not obj.customer:
            return None
        user = obj.customer.user
        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "picture": user.photo.url if user.photo else None,
        }

    def get_provider(self, obj):
        if not obj.provider:
            return None
        provider_user = obj.provider.user
        return {
            "id": obj.provider.id,
            "company_name": obj.provider.company_name,
            "logo": obj.provider.logo.url if obj.provider.logo else None,
            "picture": provider_user.photo.url if provider_user.photo else None,
        }

    def get_payment_type(self, obj):
        if obj.payment_status == "DISBURSEMENT":
            return "DISBURSED"
        if obj.payment_status == "PAID":
            return "RECEIVED"
        if obj.payment_status == "REFUND":
            return "REFUNDED"
        return obj.payment_status

    def get_status_duration(self, obj):
        now = timezone.now()
        if obj.completed_at:
            diff = now - obj.completed_at
        elif obj.started_at:
            diff = now - obj.started_at
        elif obj.accepted_at:
            diff = now - obj.accepted_at
        else:
            diff = now - obj.created_at
        days = diff.days
        hours = diff.seconds // 3600
        return f"{days}d {hours}h"

    def get_action(self, obj):
        return {
            "details": True,
            "pay_provider": (
                obj.status == "COMPLETED"
                and obj.payment_status == "PAID"
            )
        }

class AdminOrderPaymentTransactionSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = ["id", "payment_id", "transaction_id", "type", "action", "amount", "currency", "user_name", "created_at"]

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None

class AdminOrderChangesRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderChangesRequest
        fields = ["id", "request_by", "status", "changes_type", "changes_data", "created_at", "updated_at"]

class AdminOrderAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAttachment
        fields = ["id", "file", "created_at"]
    
    def get_file(self, obj):
        file = getattr(obj, "file", None)
        if file:
            request = self.context.get("request")
            return request.build_absolute_uri(file.url) if request else file.url
        return None

# ===================Order=======================

class PaymentTransactionSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="created_at", read_only=True)
    user_first_name = serializers.CharField(source="user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="user.last_name", read_only=True)
    user_picture = serializers.ImageField(source="user.photo", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = ["id", "date", "payment_id", "transaction_id", "user_first_name", "user_last_name", "user_picture", "type", "amount", "action", "order"]

class OrderRefundRequestSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(source="created_at", read_only=True)
    order_id = serializers.IntegerField(source="order.id", read_only=True)
    user_first_name = serializers.CharField(source="customer.user.first_name", read_only=True)
    user_last_name = serializers.CharField(source="customer.user.last_name", read_only=True)
    user_picture = serializers.ImageField(source="customer.user.photo", read_only=True)
    processed_by = serializers.CharField(source="processed_by.username", read_only=True)

    class Meta:
        model = OrderRefundRequest
        fields = ["id", "date", "order_id", "user_first_name", "user_last_name", "user_picture", "status", "order_amount", "refund_amount", "processed_by", "processed_at", "admin_note", "reason"]

    # def validate(self, attrs):
    #     request = self.context["request"]
    #     order = self.context["order"]
    #     if order.payment_status != OrderPaymentStatus.REFUND:
    #         raise ValidationError("Order not paid")
    #     attrs["customer"] = request.user.hasCustomerProfile
    #     attrs["order"] = order
    #     return attrs

class OrderRefundRequestActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RefundStatus.choices)
    admin_note = serializers.CharField(required=False, allow_blank=True)
    trnx_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context.get("request")
        refund = self.context.get("refund_object")
        if not refund:
            raise serializers.ValidationError("Refund object is required.")
        new_status = attrs.get("status")
        current_status = refund.status
        if current_status == new_status:
            raise serializers.ValidationError(
                {"status": f"Already in {current_status} status."}
            )

        allowed_transitions = {
            RefundStatus.PENDING: [RefundStatus.APPROVED, RefundStatus.REJECTED],
            RefundStatus.APPROVED: [RefundStatus.COMPLETED],
        }
        if current_status in allowed_transitions:
            if new_status not in allowed_transitions[current_status]:
                raise serializers.ValidationError(
                    {"status": f"Cannot change from {current_status} to {new_status}."}
                )

        if new_status == RefundStatus.COMPLETED:
            trnx_id = attrs.get("trnx_id")
            if not trnx_id:
                raise serializers.ValidationError(
                    {"trnx_id": "Transaction ID is required for completion."}
                )
        return attrs
