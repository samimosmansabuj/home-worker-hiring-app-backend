from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP, Address, CustomerProfile, ServiceProviderProfile
from .utils import generate_otp
from find_worker_config.model_choice import OTPType
from django.core.exceptions import ObjectDoesNotExist
from find_worker_config.model_choice import UserRole, UserDefault
from django.contrib.auth import get_user_model


# Login With OTP Start===========================
class LoginOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        self.phone = attrs.get("phone", None)
        self.email = attrs.get("email", None)

        if not self.phone and not self.email:
            raise serializers.ValidationError(
                "Either phone or email must be provided."
            )
        try:
            self.user = self.get_user()
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                "No user found with the provided phone/email."
            )
        return attrs

    def get_user(self):
        if self.phone:
            return User.objects.get(phone=self.phone)
        return User.objects.get(email=self.email)

    def del_unused_otp_object(self):
        OTP.objects.filter(user=self.user, purpose=OTPType.LOGIN).delete()

    def create_otp_object(self):
        self.del_unused_otp_object()
        otp_code = generate_otp(length=6)
        otp_obj = OTP.objects.create(
            phone=self.phone,
            email=self.email,
            user=self.user,
            code=otp_code,
            purpose=OTPType.LOGIN,
        )
        # self.send_otp(otp_obj.code)
        if self.phone:
            return {"phone": self.phone}
        return {"email": self.email}

class LoginOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    otp = serializers.CharField()

    def authenticated(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }
# Login With OTP End===========================

# SignUp With OTP Start===========================
class SignUpOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        if not attrs.get("phone") and not attrs.get("email"):
            raise serializers.ValidationError(
                "Either phone or email must be provided."
            )
        return attrs

class SignUpOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    otp = serializers.CharField()

    def validate(self, attrs):
        if not attrs.get("phone") and not attrs.get("email"):
            raise serializers.ValidationError(
                "Either phone or email must be provided."
            )
        if not attrs.get("otp"):
            raise serializers.ValidationError(
                "OTP must be provided."
            )
        return attrs

    def authenticated(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

class SignupSerializer(serializers.ModelSerializer):
    address = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "password", "address"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already exists")
        return value

    def create(self, validated_data):
        address_text = validated_data.pop("address")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        Address.objects.create(
            user=user,
            address_line=address_text,
            is_default=True
        )

        return user
    
    def authenticated(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

# SignUp With OTP End===========================


# User Info Current ===========================
class UserAddressSerializer(serializers.ModelSerializer):
    # user = serializers.PrimaryKeyRelatedField( queryset=User.objects.all(), write_only=True, required=False)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    class Meta:
        model = Address
        fields = "__all__"

# ---------main---------
class ServiceCategoryField(serializers.ListField):
    child = serializers.IntegerField()

    def to_representation(self, value):
        return [
            {"id": c.id, "title": c.title} for c in value.all()
        ]

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["rating", "total_orders"]
        depth = True

class ServiceProviderProfileSerializer(serializers.ModelSerializer):
    service_category = ServiceCategoryField()
    class Meta:
        model = ServiceProviderProfile
        fields = ["rating", "total_jobs", "service_category"]
        depth = True

class UserInfoSerializer(serializers.ModelSerializer):
    # password = serializers.CharField(write_only=True)
    addresses = UserAddressSerializer(required=False, many=True)
    service_category = ServiceCategoryField(required=True, source="service_provider_profile.service_category", write_only=True)
    customer_profile = CustomerProfileSerializer()
    service_provider_profile = ServiceProviderProfileSerializer()
    profile = serializers.ChoiceField(choices=UserDefault.choices, write_only=True)
    default_user = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "language", "addresses", "service_category", "customer_profile", "service_provider_profile", "profile", "default_user"]
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_mode = self.context.get("user_mode")
        if user_mode == UserDefault.CUSTOMER:
            data.pop("service_provider_profile")
        elif user_mode == UserDefault.PROVIDER:
            data.pop("customer_profile")
        else:
            data.pop("service_provider_profile")
            data.pop("customer_profile")
        return data

    def set_provider_category(self, instance, validated_data):
        user_mode = self.context.get("user_mode")
        if user_mode == UserDefault.PROVIDER and validated_data.get("service_provider_profile"):
            service_categories = validated_data["service_provider_profile"].pop("service_category", None)
            if not validated_data["service_provider_profile"]:
                validated_data.pop("service_provider_profile")
            if service_categories and hasattr(instance, "service_provider_profile"):
                provider = instance.service_provider_profile
                provider.service_category.set(service_categories)
                provider.save()
        else:
            if validated_data.get("service_provider_profile"): validated_data.pop("service_provider_profile")
        return validated_data

    def create_user_default_profile(self, user, profile_type):
        if profile_type == UserDefault.CUSTOMER:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
        elif profile_type == UserDefault.PROVIDER:
            profile, _ = ServiceProviderProfile.objects.get_or_create(user=user)
    
    def update(self, instance, validated_data):
        profile = validated_data.pop("profile", None)
        if profile in (UserDefault.CUSTOMER, UserDefault.PROVIDER):
            self.create_user_default_profile(instance, profile)
            default_user = profile
            validated_data["default_user"] = default_user
        validated_data = self.set_provider_category(instance, validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
# User Info Current ===========================
