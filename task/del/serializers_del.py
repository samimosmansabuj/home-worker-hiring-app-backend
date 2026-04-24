from ..models import ServiceCategory, ServiceSubCategory, Order, ReviewAndRating, PaymentTransaction, ServiceSubCategory, OrderRefundRequest, OrderPaymentStatus
from rest_framework import serializers
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault, ReviewRatingChoice, RefundStatus
from account.models import User
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

# ============================================================
# Category Serializers Section ===================
class ServiceSubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSubCategory
        fields = "__all__"

class ServiceCategorySerializer(serializers.ModelSerializer):
    subcategory = ServiceSubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = "__all__"

# Category Serializers Section ===================
# ============================================================



# ==========================================================================================
# =================== Order Section Start===================================
class OrderSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=ServiceSubCategory.objects.all(),
        required=False,
        allow_null=True
    )

    customer = serializers.SerializerMethodField()
    provider = serializers.SerializerMethodField()
    order_review = serializers.SerializerMethodField()
    refund_request = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("customer", "provider")

    # -----------------------------
    # VALIDATION
    # -----------------------------
    def validate(self, attrs):
        request = self.context["request"]
        profile_type = request.headers.get("profile-type", "").upper()

        # Provider cannot create order
        if profile_type == "PROVIDER":
            raise ValidationError("Provider cannot create order")

        # Prevent update after locked states
        if self.instance:
            if self.instance.status in [
                OrderStatus.CONFIRM,
                OrderStatus.IN_PROGRESS,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
                OrderStatus.REFUND,
            ]:
                raise ValidationError("Order cannot be modified in this state")

        return attrs

    # -----------------------------
    # CREATE
    # -----------------------------
    def create(self, validated_data):
        user = self.context["request"].user

        if not hasattr(user, "hasCustomerProfile"):
            raise ValidationError("Customer profile required")

        validated_data["customer"] = user.hasCustomerProfile
        return super().create(validated_data)

    # -----------------------------
    # REPRESENTATION HELPERS
    # -----------------------------
    def get_customer(self, obj):
        if not obj.customer:
            return None
        user = obj.customer.user
        return {
            "id": obj.customer.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "phone": user.phone,
        }

    def get_provider(self, obj):
        if not obj.provider:
            return None
        user = obj.provider.user
        return {
            "id": obj.provider.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "phone": user.phone,
        }

    def get_order_review(self, obj):
        review = obj.order_review.first() if hasattr(obj, "order_review") else None
        if not review:
            return None
        return {
            "rating": review.rating,
            "review": review.review,
        }

    def get_refund_request(self, obj):
        refund = getattr(obj, "refund_request", None)
        if not refund:
            return None
        return {
            "status": refund.status,
            "amount": refund.refund_amount,
        }

class ReviewAndRatingSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReviewAndRating
        fields = "__all__"
        read_only_fields = ["customer", "provider", "order"]

    def validate(self, attrs):
        request = self.context["request"]
        order = self.context["order"]

        if order.status not in [OrderStatus.COMPLETED]:
            raise ValidationError("Order not completed")

        if order.customer != request.user.hasCustomerProfile:
            raise ValidationError("Not allowed")

        attrs["customer"] = request.user.hasCustomerProfile
        attrs["provider"] = order.provider
        attrs["order"] = order

        return attrs

class OrderRefundRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderRefundRequest
        fields = "__all__"
        read_only_fields = ["customer", "order"]

    def validate(self, attrs):
        request = self.context["request"]
        order = self.context["order"]

        if order.customer != request.user.hasCustomerProfile:
            raise ValidationError("Not allowed")

        if order.payment_status != OrderPaymentStatus.PAID:
            raise ValidationError("Order not paid")

        attrs["customer"] = request.user.hasCustomerProfile
        attrs["order"] = order

        return attrs

# =================== Order Section End===================================
# ==========================================================================================




# ==========================================================================================
# =================== Payment transaction Section Start===================================
class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"

class PaymentTransactionDetailSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    provider = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        exclude = ["user"]

    def get_user(self, obj):
        return {
            "id": obj.user.id if obj.user else None,
            "name": str(obj.user) if obj.user else None,
        }

    def get_customer(self, obj):
        return {
            "id": obj.customer.id if obj.customer else None,
            "name": str(obj.customer) if obj.customer else None,
        }

    def get_provider(self, obj):
        return {
            "id": obj.provider.id if obj.provider else None,
            "name": str(obj.provider) if obj.provider else None,
        }

    def get_order(self, obj):
        if obj.order:
            return {
                "id": obj.order.id,
                "title": obj.order.title,
                "amount": obj.order.amount,
            }
        return None

# =================== Payment transaction Section End===================================
# ==========================================================================================
