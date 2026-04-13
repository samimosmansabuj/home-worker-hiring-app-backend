from rest_framework import serializers
from account.models import ServiceProviderProfile, CustomerProfile
from task.models import Order, OrderAttachment
from datetime import datetime

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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        attachments_list = OrderAttachmentSerializer(instance.order_attachments, many=True).data
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

