from .models import ServiceCategory, ServiceSubCategory, Order, ReviewAndRating, PaymentTransaction, ServiceSubCategory, OrderRefundRequest, OrderPaymentStatus, OrderAttachment, OrderChangesRequest
from rest_framework import serializers
from find_worker_config.model_choice import OrderStatus, UserDefault, OrderChangesRequestStatus, ChangesRequestType, HelperSlotExceptionType
from account.models import ServiceProviderProfile, HelperSlotException
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from datetime import datetime, timedelta
from django.db import transaction
from account.utils import generate_otp
from math import radians, cos, sin, asin, sqrt
from core.services.slot_status_engine import SlotStatusEngine

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
class OrderAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderAttachment
        fields = ["id", "file"]
    
    def get_file(self, obj):
        file = getattr(obj, "file", None)
        if file:
            request = self.context.get("request")
            return request.build_absolute_uri(file.url) if request else file.url
        return None

class OrderSerializerAll(serializers.ModelSerializer):
    provider_id = serializers.IntegerField(write_only=True)
    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    working_start_time = serializers.TimeField(
        input_formats=["%I:%M %p", "%H:%M"]
    )

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["status", "payment_status", "accepted_at", "started_at", "completed_at", "created_at", "updated_at"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        attachments_list = OrderAttachmentSerializer(instance.order_attachments, many=True, context=self.context).data
        data["attachments"] = attachments_list
        return data

    def validate_provider_id(self, value):
        if not ServiceProviderProfile.objects.filter(id=value).exists():
            raise serializers.ValidationError("Provider not found")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        provider_id = validated_data.pop("provider_id")
        attachments = validated_data.pop("attachments", [])

        validated_data["customer"] = request.user.customer_profile
        validated_data["provider"] = ServiceProviderProfile.objects.get(id=provider_id)

        order = Order.objects.create(
            **validated_data
        )
        for file in attachments:
            OrderAttachment.objects.create(order=order, file=file)
        return order

# =================================================================
class CounterSerializer(serializers.Serializer):
    budget = serializers.DecimalField(max_digits=9, decimal_places=2)
    message = serializers.CharField(required=False)

    def save(self, **kwargs):
        budget = self.validated_data.get("budget")
        message = self.validated_data.get("message")
        order = kwargs.get("order")
        profile_type = kwargs.get("profile_type")
        if OrderChangesRequest.objects.filter(order=order, status=OrderChangesRequestStatus.NO_RESPONSE).exists():
            raise ValueError("One Changes Request not response!")
        elif OrderChangesRequest.objects.filter(order=order, request_by=profile_type, changes_type=ChangesRequestType.COUNTER).exists():
            raise ValueError("Only One counter each side!")
        with transaction.atomic():
            OrderChangesRequest.objects.create(
                order=order,
                status=OrderChangesRequestStatus.ACCEPT,
                request_by=profile_type,
                changes_type=ChangesRequestType.COUNTER,
                changes_data={
                    "budget": f"{budget}",
                    "message": message
                }
            )
            order.amount = budget
            order.save()
            return order

class SetHourSerializer(serializers.Serializer):
    set_hour = serializers.IntegerField(required=True,error_messages={
            "required": "Hour is required",
            "invalid": "Hour must be a valid number",
            "null": "Hour cannot be empty"
        })
    message = serializers.CharField(required=False)

    def generate_hour_slots(self, start_dt, hours):
        slots = []
        current = start_dt

        for _ in range(hours):
            end = current + timedelta(hours=1)
            slots.append((current, end))
            current = end

        return slots

    def validate(self, attrs):
        order = self.context.get("order")
        if not order:
            raise serializers.ValidationError({
                "order": "Order is required in serializer context"
            })
        
        slot_exception = HelperSlotException.objects.filter(order=order).first()
        if slot_exception:
            slot_exception.is_active = False
            slot_exception.save()
        
        set_hour = attrs.get("set_hour") or order.working_hour
        date = order.working_date
        time = order.working_start_time

        if not date and not time and not set_hour:
            raise serializers.ValidationError("Date or time and Working Hour must be provided.")

        slot_start_dt = datetime.combine(date, time)
        # slot_end_dt = slot_start_dt + timedelta(hours=set_hour)

        slots = self.generate_hour_slots(slot_start_dt, set_hour)

        # SLOT ENGINE CALL
        status_map = {
            "BOOKED": "Already booked",
            "UNAVAILABLE": "Provider unavailable",
            "FREEZED": "Temporarily locked",
        }
        slot_engine = SlotStatusEngine()
        for slot_start, slot_end in slots:
            slot_status = slot_engine.get_status(
                provider=order.provider,
                date_obj=date,
                slot_start=slot_start,
                slot_end=slot_end
            )
            if slot_status in [HelperSlotExceptionType.BOOKED, HelperSlotExceptionType.FREEZED]:
                if slot_exception:
                    slot_exception.is_active = True
                    slot_exception.save()
                raise serializers.ValidationError({
                    "slot": status_map.get(slot_status, "Not available")
                })
        
        if slot_exception:
            slot_exception.is_active = True
            slot_exception.save()
        return attrs

    def save(self, **kwargs):
        available_status = [OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS]
        hour = self.validated_data.get("set_hour")
        message = self.validated_data.get("message")
        order = kwargs.get("order")
        if order.status not in available_status:
            raise ValueError(f"Set Hour not accept when order is {order.status}")
        
        with transaction.atomic():
            OrderChangesRequest.objects.create(
                order=order,
                status=OrderChangesRequestStatus.ACCEPT,
                request_by=UserDefault.PROVIDER,
                changes_type=ChangesRequestType.SET_HOUR,
                changes_data={
                    "hour": f"{hour}",
                    "message": message
                }
            )
            order.working_hour = hour
            order.save(update_fields=["working_hour"])
            return order

class ProposeNewTimeSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    time = serializers.TimeField(input_formats=["%I:%M %p", "%H:%M"])
    message = serializers.CharField(required=False)

    def validate(self, attrs):
        order = self.context.get("order")
        if not order:
            raise serializers.ValidationError({
                "order": "Order is required in serializer context"
            })
        
        date = attrs.get("date") or order.working_date
        time = attrs.get("time") or order.working_start_time

        if not date and not time:
            raise serializers.ValidationError("Date or time must be provided.")

        slot_start_dt = datetime.combine(date, time)
        slot_end_dt = slot_start_dt + timedelta(hours=order.working_hour)

        # SLOT ENGINE CALL
        slot_engine = SlotStatusEngine()
        slot_status = slot_engine.get_status(
            provider=order.provider,
            date_obj=date,
            slot_start=slot_start_dt,
            slot_end=slot_end_dt
        )

        if slot_status != HelperSlotExceptionType.AVAILABLE:
            status_map = {
                "BOOKED": "Already booked",
                "UNAVAILABLE": "Provider unavailable",
                "FREEZED": "Temporarily locked",
            }
            raise serializers.ValidationError({
                "slot": status_map.get(slot_status, "Not available")
            })
        return attrs

    def get_data(self, order, profile_type, validated_data):
        date = validated_data.get("date", None)
        time = validated_data.get("time", None)
        message = validated_data.get("message", None)
        data = {
            "order": order,
            "status": OrderChangesRequestStatus.NO_RESPONSE,
            "request_by": profile_type
        }

        changes_data = {"message": message}

        if date and time:
            data["changes_type"] = ChangesRequestType.TIME_AND_DATE
            changes_data.update({
                "date": date.isoformat(),
                "time": time.isoformat(),
                # "time": time.strftime("%H:%M:%S"),
            })

        elif date:
            data["changes_type"] = ChangesRequestType.DATE
            changes_data.update({
                "date": date.isoformat(),
            })

        elif time:
            data["changes_type"] = ChangesRequestType.TIME
            changes_data.update({
                "time": time.isoformat(),
            })
        else:
            raise ValueError("Time or date must be submit!")
        data["changes_data"] = changes_data
        response_message = "Request sent successfully"
        return data, response_message

    def save(self, **kwargs):
        order = kwargs.get("order")
        profile_type = kwargs.get("profile_type")

        if OrderChangesRequest.objects.filter(
            order=order,
            status=OrderChangesRequestStatus.NO_RESPONSE
        ).exists():
            raise ValueError("Already sent a request!")
        data, response_message = self.get_data(
            order,
            profile_type,
            self.validated_data
        )

        with transaction.atomic():
            self.response_message = response_message
            return OrderChangesRequest.objects.create(**data)
    
    def get_response_message(self):
        return self.response_message

class ProposeNewTimeActionSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)
    request_id = serializers.IntegerField(required=True, write_only=True)

    def validate_slot(self, order, changes_request):
        changes_data = changes_request.changes_data
        date_obj = order.working_date
        slot_start = order.working_start_time

        if changes_request.changes_type in [ChangesRequestType.TIME_AND_DATE, ChangesRequestType.DATE]:
            date_str = changes_data.get("date")
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        if changes_request.changes_type in [ChangesRequestType.TIME_AND_DATE, ChangesRequestType.TIME]:
            time_str = changes_data.get("time")
            slot_start = datetime.strptime(time_str, "%H:%M:%S").time()

        slot_start_dt = datetime.combine(date_obj, slot_start)
        slot_end_dt = (
            datetime.combine(date_obj, slot_start) +
            timedelta(hours=order.working_hour)
        )

        # SLOT ENGINE CALL
        slot_engine = SlotStatusEngine()
        slot_status = slot_engine.get_status(
            provider=order.provider,
            date_obj=date_obj,
            slot_start=slot_start_dt,
            slot_end=slot_end_dt
        )

        status_map = {
            "BOOKED": "Already booked",
            "UNAVAILABLE": "Provider unavailable",
            "FREEZED": "Temporarily locked"
        }
        if slot_status != HelperSlotExceptionType.AVAILABLE:
            raise ValueError(status_map.get(slot_status, "Not available"))

    def get_response_message(self):
        return self.response_message
    
    def order_update(self, order, changes_request):
        if changes_request.changes_type == ChangesRequestType.TIME_AND_DATE:
            changes_data = changes_request.changes_data
            date_str = changes_data.get("date")
            time_str = changes_data.get("time")
            order.working_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            order.working_start_time = datetime.strptime(time_str, "%H:%M:%S").time()
            self.response_message = "Propose New Time & Date Accept!"
        elif changes_request.changes_type == ChangesRequestType.DATE:
            changes_data = changes_request.changes_data
            date_str = changes_data.get("date")
            order.working_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            self.response_message = "Propose New Date Accept!"
        elif changes_request.changes_type == ChangesRequestType.TIME:
            changes_data = changes_request.changes_data
            time_str = changes_data.get("time")
            order.working_start_time = datetime.strptime(time_str, "%H:%M:%S").time()
            self.response_message = "Propose New Time Accept!"
        order.save()
        return order
    
    def save(self, **kwargs):
        order = kwargs.get("order")
        request_id = self.validated_data.get("request_id", None)
        profile_type = kwargs.get("profile_type")
        changes_request = OrderChangesRequest.objects.get(id=request_id, order=order)
        status = self.validated_data.get("status", None)
        if changes_request.request_by == profile_type:
            raise ValueError("You can't action your request.")
        elif changes_request.status in [OrderChangesRequestStatus.ACCEPT, OrderChangesRequestStatus.DECLINED]:
            raise ValueError(f"This request is alread {changes_request.status}")
        
        with transaction.atomic():
            status = status.upper()
            changes_request.status = status
            changes_request.save()
            if status == OrderChangesRequestStatus.ACCEPT:
                self.validate_slot(order, changes_request)
                order = self.order_update(order, changes_request)
                return order
            if status == OrderChangesRequestStatus.DECLINED:
                self.response_message = f"Time Changes Request {status}"
                return order

class StartWorkSerializer(serializers.Serializer):
    start = serializers.BooleanField(required=True)
    address = serializers.CharField(required=False)
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)

    def is_within_100m(self, lat1, lon1, lat2, lon2):
        lon1, lat1, lon2, lat2 = map(
            radians, [lat1, lon1, lon2, lat2]
        )
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        distance_km = 6371 * c
        distance_m = distance_km * 1000
        return distance_m <= 100

    def work_start(self, **kwargs):
        order = kwargs.get("order")
        start = self.validated_data.get("start", None)
        address = self.validated_data.get("address", None)
        helper_lat = self.validated_data.get("lat", None)
        helper_lng = self.validated_data.get("lng", None)
        if start and helper_lat and helper_lng and order:
            with transaction.atomic():
                order_lat = order.lat
                order_lng = order.lng
                is_near = self.is_within_100m(helper_lat, helper_lng, order_lat, order_lng)
                if not is_near:
                    raise ValueError("You are not under 100m at work space!")
                order.status = OrderStatus.IN_PROGRESS
                order.confirmation_OTP = generate_otp(6)
                order.save(update_fields=["status", "confirmation_OTP"])
                return order
        else:
            raise ValueError("Something wrong!")

class CompleteSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True)

    def complete(self, **kwargs):
        order = kwargs.get("order")
        otp = self.validated_data.get("otp", None)
        if otp and order.confirmation_OTP == otp:
            with transaction.atomic():
                order.status = OrderStatus.COMPLETED
                order.save(update_fields=["status"])
                return order
        else:
            raise ValueError("OTP or Invalid OTP")

class ReviewAndRatingSerializer(serializers.ModelSerializer):
    review = serializers.CharField(required=True)
    
    class Meta:
        model = ReviewAndRating
        fields = ["id", "order", "customer", "provider", "send_by", "rating", "review", "is_approved", "created_at", "updated_at"]
        read_only_fields = ["id", "order", "customer", "provider", "send_by", "is_approved", "created_at", "updated_at"]
    
    def create(self, validated_data):
        with transaction.atomic():
            order = self.context.get("order")
            send_by = self.context.get("send_by")
            if not any(order and send_by):
                raise ValueError("Somthing Wrong!")
            if ReviewAndRating.objects.filter(order=order, send_by=send_by).filter():
                raise ValueError("Your feedback already submited!")
            validated_data["order"] = order
            validated_data["customer"] = order.customer
            validated_data["provider"] = order.provider
            validated_data["send_by"] = send_by
            return super().create(validated_data)

# Not Work Yet--
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

# ==================================================================
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
