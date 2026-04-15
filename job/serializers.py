from rest_framework import serializers
from account.models import ServiceProviderProfile, CustomerProfile
from task.models import Order, OrderAttachment, OrderChangesRequest
from datetime import datetime
from find_worker_config.model_choice import OrderChangesRequestStatus, OrderStatus, UserDefault, ChangesRequestType
from django.db import transaction

# helper list serializer---
class ProviderSerializer(serializers.ModelSerializer):
    # user fields
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    photo = serializers.ImageField(source="user.photo", read_only=True)

    # email
    # phone

    service_category = serializers.SerializerMethodField()
    office_location = serializers.SerializerMethodField()

    distance_km = serializers.FloatField(read_only=True)

    class Meta:
        model = ServiceProviderProfile
        fields = [
            "id",

            "first_name",
            "last_name",
            "username",
            "photo",
            
            "company_name",
            "logo",
            "details",
            "hourly_rate",
            "min_booking_hours",
            "availability_status",
            "is_verified",

            "complete_rate",
            "rating",
            "total_jobs",

            "service_category",
            "office_location",
            "distance_km"
        ]

    def get_service_category(self, obj):
        return [
            {"id": cat.id, "title": cat.title}
            for cat in obj.service_category.all()
        ]

    def get_office_location(self, obj):
        office = obj.office_location
        if not office:
            return None
        return {
            "id": office.id,
            "address_line": office.address_line,
            "city": office.city,
            "lat": office.lat,
            "lng": office.lng,
        }




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

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["status", "payment_status", "accepted_at", "started_at", "completed_at", "created_at", "updated_at"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        attachments_list = OrderAttachmentSerializer(instance.order_attachments, many=True, context=self.context).data
        data["attachments"] = attachments_list
        return data

    def validate_working_start_time(self, value):
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, "%I:%M %p").time()
            except ValueError:
                raise serializers.ValidationError(
                    "Invalid time format. Use '10:00 AM' or '14:00'"
                )
        return value

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

    def convert_hour_to_munite(self, hour):
        return float(hour) * 60

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
            order.working_hour = self.convert_hour_to_munite(hour)
            order.save(update_fields=["working_hour"])
            return order

class ProposeNewTimeSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    time = serializers.TimeField(required=False)
    message = serializers.CharField(required=False)

    def get_data(self, order, profile_type):
        date = self.validated_data.get("date", None)
        time = self.validated_data.get("time", None)
        message = self.validated_data.get("message", None)
        data = {
            "order": order,
            "status": OrderChangesRequestStatus.NO_RESPONSE,
            "request_by": profile_type
        }
        if date and time:
            response_message = "Time and Date Changes Request Send!"
            data["changes_type"] = ChangesRequestType.TIME_AND_DATE
            data["changes_data"] = {
                "date": date.isoformat(),
                "time": time.isoformat(),
                "message": message
            }
        elif date:
            response_message = "Date Changes Request Send!"
            data["changes_type"] = ChangesRequestType.DATE
            data["changes_data"] = {
                "date": date.isoformat(),
                "message": message
            }
        elif time:
            response_message = "Time Changes Request Send!"
            data["changes_type"] = ChangesRequestType.TIME
            data["changes_data"] = {
                "time": time.isoformat(),
                "message": message
            }
        else:
            raise ValueError("Time or date must be submit!")
        return data, response_message

    def save(self, **kwargs):
        order = kwargs.get("order")
        profile_type = kwargs.get("profile_type")
        if OrderChangesRequest.objects.filter(order=order, changes_type__in=[ChangesRequestType.TIME_AND_DATE, ChangesRequestType.DATE, ChangesRequestType.TIME], status=OrderChangesRequestStatus.NO_RESPONSE):
            raise ValueError("Already send a request!")
        data, response_message = self.get_data(order,  profile_type)
        with transaction.atomic():
            self.response_message = response_message
            changes_request = OrderChangesRequest.objects.create(**data)
            return changes_request
    
    def get_response_message(self):
        return self.response_message

class ProposeNewTimeActionSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)
    request_id = serializers.IntegerField(required=True, write_only=True)

    def get_response_message(self):
        return self.response_message
    
    def order_update(self, order, changes_request):
        if changes_request.changes_type == ChangesRequestType.TIME_AND_DATE:
            changes_data = changes_request.changes_data
            order.working_date = changes_data.get("date")
            order.working_start_time = changes_data.get("time")
            self.response_message = "Propose New Time & Date Accept!"
        elif changes_request.changes_type == ChangesRequestType.DATE:
            changes_data = changes_request.changes_data
            order.working_date = changes_data.get("date")
            self.response_message = "Propose New Date Accept!"
        elif changes_request.changes_type == ChangesRequestType.TIME:
            changes_data = changes_request.changes_data
            order.working_start_time = changes_data.get("time")
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
                order = self.order_update(order, changes_request)
                return order

class StartWorkSerializer(serializers.Serializer):
    start = serializers.BooleanField(required=True)
    address = serializers.CharField(required=False)
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)

    def work_start(self, **kwargs):
        order = kwargs.get("order")
        start = self.validated_data.get("start", None)
        address = self.validated_data.get("address", None)
        helper_lat = self.validated_data.get("lat", None)
        helper_lng = self.validated_data.get("lng", None)

        if start and helper_lat and helper_lng and order:
            order_lat = order.lat
            order_lng = order.lng
            
        else:
            raise ValueError("Something wrong!")
    
# ==================================================================


