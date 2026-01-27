from .models import ServiceCategory, Order, OrderRequest, ReviewAndRating
from rest_framework import serializers
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault, ReviewRatingChoice
from account.models import User
from django.shortcuts import get_object_or_404

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

class ReviewAndRatingSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = ReviewAndRating
        fields = "__all__"
        read_only_fields = ["customer", "provider"]

    def validate(self, attrs):
        order = attrs.get("order")
        if order.status not in (OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE):
            raise Exception("This order isn't Complete!")
        request = self.context.get("request")
        user = request.user
        if order.customer != user.customer:
            raise Exception("You can't create review for this order!")
        provider = order.provider
        if not provider:
            raise Exception("Provider has been empty!")
        attrs["customer"] = user.customer
        attrs["provider"] = provider
        return attrs

class OrderSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ServiceCategory.objects.all())
    order_requests = OrderRequestSerializerForOrder(many=True, read_only=True, source="order_requests.order_by")
    service_data = serializers.DateTimeField(required=True)
    # order_review = ReviewAndRatingSerializerForOrder(read_only=True)
    order_review = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("customer", "provider", "order_review")
    
    def validate(self, attrs):
        request = self.context.get("request")
        profile_type = request.headers.get("profile-type", "").upper()
        method = request.method
        instance = self.instance
        if instance and request.method in ("PATCH", "PUT"):
            if instance.status in (
                OrderStatus.CONFIRM,
                OrderStatus.IN_PROGRESS,
                OrderStatus.COMPLETED,
                OrderStatus.PARTIAL_COMPLETE,
                OrderStatus.CANCELLED,
                OrderStatus.REFUND,
            ):
                raise serializers.ValidationError(
                    f"Order cannot be updated when status is {instance.status}"
                )
            
        
        if profile_type.upper() == UserDefault.PROVIDER:
            raise Exception("Provider can't Update or Create Order Details.")
        elif profile_type.upper() == UserRole.ADMIN:
            if method in ("POST"):
                raise Exception("Admin can't create an Order.")
        
        if attrs.get("budget_min") and attrs.get("budget_max"):
            if attrs.get("budget_min") > attrs.get("budget_max"):
                raise Exception("Minimum budget cannot exceed maximum budget!")
        return attrs

    def to_representation(self, instance):
        request = self.context.get("request")
        def build_user_profile(id, user):
            return {
                "id": id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "photo": request.build_absolute_uri(user.photo.url) if user.photo else None,
                "email": user.email,
                "phone": user.phone,
            }
        category = {
            "id": instance.category.id,
            "title": instance.category.title,
            "description": instance.category.description,
            "icon": instance.category.icon
        }
        customer = build_user_profile(instance.customer.id, instance.customer.user)
        provider = build_user_profile(instance.provider.id, instance.provider.user) if instance.provider else None

        # custom data representation
        data = super().to_representation(instance)
        new_data = {
            "id": data["id"],
            "category": category,
            "customer": customer,
            "provider": provider,
            "title": data["title"],
            "description": data["description"],
            "area": data["area"],
            "status": data["status"],
            "payment_status": data["payment_status"]
        }
        
        # show amount according to status 
        if data["status"] in (OrderStatus.ACTIVE):
            new_data["budget_min"] = data["budget_min"]
            new_data["budget_max"] = data["budget_max"]
        else:
            # new_data["provider"] = data["provider"]
            new_data["amount"] = data["amount"]
        
        # meta data 
        new_data["service_data"] = data["service_data"]
        new_data["updated_at"] = data["updated_at"]
        new_data["created_at"] = data["created_at"]
        
        # representation oder request
        new_data["total_order_requests"] = len(data["order_requests"])
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
        
        # representation order review
        order_review = get_object_or_404(ReviewAndRating, pk=data.get("order_review")) if data.get("order_review") else None
        if instance.status in [OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE]:
            if order_review:
                review ={
                    "id": order_review.id,
                    "rating": order_review.rating,
                    "review": order_review.review,
                    "created": order_review.created,
                }
                new_data["order_review"] = review
            else:
                new_data["order_review"] = order_review

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
    class Meta:
        model = OrderRequest
        fields = "__all__"
        read_only_fields = ["provider"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data
    
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

class ReviewAndRatingSerializer(serializers.ModelSerializer):
    rating = serializers.ChoiceField(choices=ReviewRatingChoice.choices, required=True)
    class Meta:
        model = ReviewAndRating
        fields = "__all__"
        read_only_fields = ["customer", "provider", "order"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        new_data = {
            "id": data.get("id"),
            "rating": data.get("rating"),
            "review": data.get("review"),
            "created": data.get("created"),
        }

        customer_object = instance.customer
        provider_object = instance.provider
        order_object = instance.order
        request = self.context.get("request")
        present = self.context.get("present", None)

        if present is None:
            def build_user_profile(id, user):
                return {
                    "id": id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "photo": request.build_absolute_uri(user.photo.url) if user.photo else None,
                    "email": user.email,
                    "phone": user.phone,
                }
            customer = build_user_profile(customer_object.id, customer_object.user)
            provider = build_user_profile(provider_object.id, provider_object.user)
            order = {
                "id": order_object.id,
                "title": order_object.title,
                "status": order_object.status,
            }

            new_data["order"] = order
            new_data["customer"] = customer
            new_data["provider"] = provider
        return new_data

    def validate(self, attrs):
        order = self.context.get("order")

        # Customer Check & Permission---------
        request = self.context.get("request")
        if order.customer != request.user.hasCustomerProfile:
            raise Exception("You can't create review for this order!")
        
        # Provider Check
        if not order.provider:
            raise Exception("Provider has been empty!")

        # Order Status Check & Error Handling
        if order.status not in (OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE):
            raise Exception("This order isn't Complete!")
        
        attrs["order"] = order
        attrs["customer"] = request.user.hasCustomerProfile
        attrs["provider"] = order.provider
        return attrs
