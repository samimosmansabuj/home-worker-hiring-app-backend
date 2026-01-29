from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP, Address, CustomerProfile, ServiceProviderProfile, ProviderVerification
from .utils import generate_otp
from find_worker_config.model_choice import OTPType
from django.core.exceptions import ObjectDoesNotExist
from find_worker_config.model_choice import UserRole, UserDefault
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from django.core.mail import send_mail

# =================================================================
# Login With OTP Start===========================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def get_user(self):
        return self.user

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
# =================================================================

# =================================================================
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
            raise Exception(
                "Either phone or email must be provided."
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
        self.user = user
        return user
    
    def send_code(self):
        otp = OTP.objects.create(
            user=self.user,
            email=self.user.email,
            purpose=OTPType.SIGNUP
        )
        return otp.email

# SignUp With OTP End===========================
# =================================================================

# =================================================================
# Password Change & Reset---------------
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        self.user_email = value
        return value
    
    def get_user(self):
        return User.objects.get(email=self.user_email)
    
    def send_code(self):
        # send_mail(
        #     subject="Password Reset",
        #     message=f"Reset your password using this link:\n{reset_link}",
        #     from_email=settings.DEFAULT_FROM_EMAIL,
        #     recipient_list=[user.email],
        # )
        otp = OTP.objects.create(
            user=self.get_user(),
            email=self.user_email,
            purpose=OTPType.RESET_PASSWORD
        )
        return otp.email if otp.email else otp.phone

class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        self.password = value
        return value
    
    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise Exception("email or phone is required")
        return super().validate(attrs)
    
    def set_new_password(self, user):
        user.set_password(self.password)
        user.save()
        return True

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_new_password= serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value
    
    def validate(self, attrs):
        if attrs.get("confirm_new_password") != attrs.get("new_password"):
            raise Exception("New password & confirm password not same.")
        request = self.context.get("request")
        user = request.user
        if not user.check_password(attrs["old_password"]):
            raise ValidationError({"old_password": "Wrong password"})
        self.new_set_password = attrs.get("new_password")
        return user
    
    def set_password(self):
        user = self.validated_data
        user.set_password(self.new_set_password)
        user.save()
        return True

# Password Change & Reset---------------
# =================================================================

# =================================================================
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
    addresses = UserAddressSerializer(required=False, many=True)
    service_category = ServiceCategoryField(required=True, source="service_provider_profile.service_category", write_only=True)
    customer_profile = CustomerProfileSerializer()
    service_provider_profile = ServiceProviderProfileSerializer()
    profile = serializers.ChoiceField(choices=UserDefault.choices, write_only=True)
    default_user = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "phone", "photo", "language", "addresses", "service_category", "customer_profile", "service_provider_profile", "profile", "default_user"]
    
    def get_photo_url(self, photo, request):
        if photo and request:
            return request.build_absolute_uri(photo)
        else:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_mode = self.context.get("user_mode")
        request = self.context.get("request")
        data["photo"] = self.get_photo_url(data.get("photo"), request)
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





class ProviderVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderVerification
        fields = "__all__"
        read_only_fields = ["provider"]
    
    def validate(self, attrs):
        document = attrs.get("document")
        if not document:
            raise ValidationError("Document must be submitted.")
        return super().validate(attrs)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request.user.role == UserRole.USER:
            data.pop("provider", None)
        elif request.user.role == UserRole.ADMIN:
            def build_user_profile(id, user):
                return {
                    "id": id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "photo": request.build_absolute_uri(user.photo.url) if user.photo else None,
                    "email": user.email,
                    "phone": user.phone,
                }
            data["provider"] = build_user_profile(instance.provider.id, instance.provider.user)
        return data
# User Info Current ===========================
# =================================================================

