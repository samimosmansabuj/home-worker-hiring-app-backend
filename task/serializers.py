from .models import ServiceCategory, Order, OrderRequest
from rest_framework import serializers
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault
from account.models import User

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [ "id", "title", "description", "icon", "is_active", "updated_at", "created_at"]



class OrderRequestSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = OrderRequest
        fields = ["id", "provider", "message", "budget", "status", "created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        provider = User.objects.get(service_provider_profile__id=data.pop("provider"))
        data["provider"] = {
            "id": provider.id,
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "email": provider.email,
            "phone": provider.phone,
        }
        return data


class OrderSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())
    order_requests = OrderRequestSerializerForOrder(many=True, read_only=True, source="order_requests.order_by")
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("customer",)
    
    def validate(self, attrs):
        if attrs.get("budget_min") and attrs.get("budget_max"):
            if attrs.get("budget_min") > attrs.get("budget_max"):
                raise Exception("Minimum budget cannot exceed maximum budget!")
        return attrs
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        category = {
            "id": instance.category.id,
            "title": instance.category.title,
            "description": instance.category.description,
            "icon": instance.category.icon
        }
        new_data = {
            "id": data["id"],
            "category": category,
            "title": data["title"],
            "description": data["description"],
            "area": data["area"],
            "status": data["status"]
        }
        if data["status"] in (OrderStatus.PENDING, OrderStatus.ACTIVE):
            new_data["budget_min"] = data["budget_min"]
            new_data["budget_max"] = data["budget_max"]
        else:
            new_data["provider"] = data["provider"]
            new_data["amount"] = data["amount"]
        
        new_data["service_data"] = data["service_data"]
        new_data["updated_at"] = data["updated_at"]
        new_data["created_at"] = data["created_at"]
        
        new_data["total_order_requests"] = len(data["order_requests"])
        request = self.context.get("request")
        if request:
            user = request.user
            if user.role == UserRole.USER and instance.order_requests.filter(provider=user.hasServiceProviderProfile).exists():
                provider_id = user.id
                new_data["order_requests"] = [
                    req
                    for req in data.get("order_requests", [])
                    if req.get("provider", {}).get("id", {}) == provider_id
                ]
            elif user.role == UserRole.USER and user.hasCustomerProfile == instance.customer:
                new_data["order_requests"] = data["order_requests"]
            elif user.role == UserRole.ADMIN:
                new_data["order_requests"] = data["order_requests"]
        return new_data
    
    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        profile = user.hasCustomerProfile
        if not profile:
            raise Exception("Customer profile required.")
        validated_data["customer"] = profile
        return super().create(validated_data)


class OrderRequestSerializer(serializers.ModelSerializer):
    # provider = serializers.HiddenField(default=serializers.CurrentUserDefault())
    # order = OrderSerializer()
    class Meta:
        model = OrderRequest
        fields = "__all__"
        read_only_fields = ["provider"]
    
    def validate(self, attrs):
        order = self.context["order"]
        request = self.context.get("request")
        user = request.user
        profile_type = request.headers.get("PROFILE-TYPE")
        if not profile_type:
            raise Exception("Profile Type must be set in headers.")
        if order.customer.user == user:
            raise Exception("Same user can't send order request.")
        if profile_type.upper() != UserDefault.PROVIDER:
            raise Exception("Only providers can send order requests.")
        if OrderRequest.objects.filter(order=order, provider=user.hasServiceProviderProfile).exists():
            raise Exception("You already applied for this order.")
        if not (order.budget_min <= attrs["budget"] <= order.budget_max):
            raise Exception("Budget out of range.")
        attrs["provider"] = user.hasServiceProviderProfile
        return attrs





# class ServiceTaskForUserSerializer(serializers.ModelSerializer):
#     customer = serializers.HiddenField(default=serializers.CurrentUserDefault())
#     category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())


#     class Meta:
#         model = ServiceTask
#         fields = "__all__"

#     def validate(self, attrs):
#         if attrs.get("budget_min") and attrs.get("budget_max"):
#             if attrs.get("budget_min") > attrs.get("budget_max"):
#                 raise serializers.ValidationError("Minimum budget cannot exceed maximum budget")
#         return attrs
    
#     def to_representation(self, instance):
#         data = super().to_representation(instance)
#         data["category"] = {
#             "id": instance.category.id,
#             "title": instance.category.title,
#             "description": instance.category.description,
#             "icon": instance.category.icon,
#         }
#         return data
    
#     def create(self, validated_data):
#         return super().create(validated_data)


# class ServicePrototypeReadSerializer(serializers.ModelSerializer):
#     category = ServiceCategorySerializer()
#     service_provider = serializers.StringRelatedField()

#     class Meta:
#         model = ServicePrototype
#         fields = "__all__"

# class ServicePrototypeWriteSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = ServicePrototype
#         exclude = ["service_provider", "status"]

#     def validate(self, attrs):
#         if attrs["budget_min"] > attrs["budget_max"]:
#             raise serializers.ValidationError("Invalid budget range")
#         return attrs

#     def create(self, validated_data):
#         user = self.context["request"].user

#         if user.role != "PROVIDER":
#             raise serializers.ValidationError("Only providers can create prototypes")

#         return ServicePrototype.objects.create(
#             service_provider=user,
#             **validated_data
#         )


# class TaskRequestReadSerializer(serializers.ModelSerializer):
#     provider = serializers.StringRelatedField()
#     task = ServiceTaskForUserSerializer()

#     class Meta:
#         model = TaskRequest
#         fields = "__all__"

# class TaskRequestWriteSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = TaskRequest
#         exclude = ["provider", "status"]

#     def validate(self, attrs):
#         task = attrs["task"]
#         user = self.context["request"].user

#         if user.role != "PROVIDER":
#             raise serializers.ValidationError("Only providers can send job requests")

#         if TaskRequest.objects.filter(task=task, provider=user).exists():
#             raise serializers.ValidationError("You already applied for this task")

#         if not (task.budget_min <= attrs["budget"] <= task.budget_max):
#             raise serializers.ValidationError("Budget out of task range")

#         return attrs

#     def create(self, validated_data):
#         user = self.context["request"].user
#         return TaskRequest.objects.create(
#             provider=user,
#             **validated_data
#         )


# def get_serializer_class(self):
#     if self.request.method in ["POST", "PUT", "PATCH"]:
#         return ServiceTaskWriteSerializer
#     return ServiceTaskForUserSerializer

