from .models import Order, ReviewAndRating, OrderRefundRequest, OrderPaymentStatus
from rest_framework import serializers
from find_worker_config.model_choice import OrderStatus
from account.models import User
from rest_framework.exceptions import ValidationError

class OrderCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = [
            "category", "subcategory", "title", "description",
            "area", "lat", "lng",
            "working_date", "working_start_time"
        ]

    def validate(self, attrs):
        request = self.context["request"]

        if not hasattr(request.user, "hasCustomerProfile"):
            raise ValidationError("Customer profile required")

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user

        validated_data["customer"] = user.hasCustomerProfile
        validated_data["status"] = OrderStatus.PENDING

        # generate OTP
        validated_data["confirmation_OTP"] = str(secrets.randbelow(999999)).zfill(6)

        return super().create(validated_data)


class OrderNegotiationSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "counter", "decline"])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate(self, attrs):
        order = self.context["order"]
        user = self.context["request"].user

        if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPT]:
            raise ValidationError("Negotiation not allowed")

        if attrs["action"] == "counter" and not attrs.get("amount"):
            raise ValidationError("Counter requires amount")

        return attrs

    def save(self):
        order = self.context["order"]
        user = self.context["request"].user
        action = self.validated_data["action"]

        if action == "accept":
            order.status = OrderStatus.ACCEPT
            if not order.provider:
                order.provider = user.hasServiceProviderProfile

        elif action == "counter":
            order.amount = self.validated_data["amount"]

        elif action == "decline":
            order.status = OrderStatus.CANCELLED

        order.save()
        return order


class OrderPaymentSerializer(serializers.Serializer):
    transaction_id = serializers.CharField()

    def validate(self, attrs):
        order = self.context["order"]

        if order.status != OrderStatus.ACCEPT:
            raise ValidationError("Order not ready for payment")

        return attrs

    def save(self):
        order = self.context["order"]

        order.payment_status = OrderPaymentStatus.PAID
        order.status = OrderStatus.CONFIRM

        # 🔥 SLOT BOOK HERE
        # create slot exception or booking lock

        order.save()
        return order


from geopy.distance import geodesic

class OrderStartSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()

    def validate(self, attrs):
        order = self.context["order"]

        if order.status != OrderStatus.CONFIRM:
            raise ValidationError("Cannot start work")

        distance = geodesic(
            (order.lat, order.lng),
            (attrs["lat"], attrs["lng"])
        ).meters

        if distance > 100:
            raise ValidationError("You must be within 100 meters")

        return attrs

    def save(self):
        order = self.context["order"]
        order.status = OrderStatus.IN_PROGRESS
        order.save()
        return order

class OrderCompleteSerializer(serializers.Serializer):
    otp = serializers.CharField()

    def validate(self, attrs):
        order = self.context["order"]

        if order.status != OrderStatus.IN_PROGRESS:
            raise ValidationError("Order not in progress")

        if order.confirmation_OTP != attrs["otp"]:
            raise ValidationError("Invalid OTP")

        return attrs

    def save(self):
        order = self.context["order"]
        order.status = OrderStatus.COMPLETED
        order.save()
        return order

class OrderRescheduleSerializer(serializers.Serializer):
    working_date = serializers.DateField()
    working_start_time = serializers.TimeField()

    def validate(self, attrs):
        order = self.context["order"]

        if order.status not in [OrderStatus.CONFIRM]:
            raise ValidationError("Cannot reschedule now")

        return attrs

    def save(self):
        order = self.context["order"]

        order.working_date = self.validated_data["working_date"]
        order.working_start_time = self.validated_data["working_start_time"]

        # 🔥 update slot booking here

        order.save()
        return order

class OrderReviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReviewAndRating
        fields = ["rating", "review"]

    def validate(self, attrs):
        order = self.context["order"]

        if order.status != OrderStatus.COMPLETED:
            raise ValidationError("Order not completed")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        order = self.context["order"]

        return ReviewAndRating.objects.create(
            order=order,
            customer=order.customer,
            provider=order.provider,
            **validated_data
        )

class OrderRefundSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderRefundRequest
        fields = ["reason"]

    def validate(self, attrs):
        order = self.context["order"]

        if order.status != OrderStatus.CONFIRM:
            raise ValidationError("Refund not allowed")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        order = self.context["order"]

        return OrderRefundRequest.objects.create(
            order=order,
            customer=request.user.hasCustomerProfile,
            **validated_data
        )

class OrderDetailSerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField()
    provider = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = "__all__"




