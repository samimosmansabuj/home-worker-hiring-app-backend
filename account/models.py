from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from find_worker_config.model_choice import  UserRole, UserLanguage, UserStatus, PaymentMethodType, OTPType, UserDefault
from .managers import CustomUserManager
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .utils import generate_otp

# Custom User Model====================================
class User(AbstractBaseUser, PermissionsMixin):
    role = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.USER)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=255, unique=True, blank=True,  null=True)
    phone = models.CharField(max_length=20, unique=True, blank=True,  null=True)
    photo = models.ImageField(upload_to="user/photo/", blank=True, null=True)
    default_user = models.CharField(max_length=30, choices=UserDefault.choices, blank=True, null=True)
    
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=UserStatus.choices, default=UserStatus.PENDING)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    language = models.CharField(max_length=10, choices=UserLanguage.choices, default=UserLanguage.EN)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone"]

    objects = CustomUserManager()

    @property
    def hasCustomerProfile(self):
        return self.customer_profile or None
    
    @property
    def hasServiceProviderProfile(self):
        return self.service_provider_profile or None
    
    def generate_username(self):
        if self.first_name and self.last_name:
            username = f"{self.first_name.replace(" ", "")}{self.last_name.replace(" ", "")}"
        elif self.first_name:
            username = self.first_name.replace(" ", "")
        elif self.last_name:
            username = self.last_name.replace(" ", "")
        elif self.email:
            username = self.email.split("@")[0].replace(".", "")
        elif self.phone:
            username = f"user{self.phone}"
        else:
            raise ValueError("Cannot generate username")
        return username.lower()

    def save(self, *args, **kwargs):
        if not self.username: self.username = self.generate_username()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"

# Customer User Profile==================================
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    rating = models.FloatField(default=0)
    total_orders = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - Customer Profile"

# Service Provider Profile================================
class ServiceProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="service_provider_profile")
    rating = models.FloatField(default=0)
    total_jobs = models.PositiveIntegerField(default=0)
    service_category = models.ManyToManyField("task.ServiceCategory", blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - Provider Profile"

# Address Model===========================================
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    profile_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    service = GenericForeignKey('profile_type', 'object_id')

    address_line = models.TextField()
    city = models.CharField(max_length=100, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_line} for {self.user}"

# Payment Method Model=====================================
class PaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    method_type = models.CharField(max_length=30, choices=PaymentMethodType.choices)
    provider = models.CharField(max_length=50)
    masked_number = models.CharField(max_length=20)


# OTP Send Model==========================================
class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    code = models.CharField(max_length=6, blank=True, null=True)
    purpose = models.CharField(max_length=20, choices=OTPType.choices)

    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).seconds > 300
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_otp(length=6)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        use = "No Used" if self.is_used is False else "Used"
        expired = "No Expired" if self.is_expired() is False else "Expired"
        return f"Your {self.purpose} OTP is {self.code} | {use} & {expired}"


# Logs Model==============================================
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    entity_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    entity_id = models.PositiveBigIntegerField(blank=True, null=True)
    service = GenericForeignKey('entity_type', 'entity_id')
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)
    need_notify = models.BooleanField(default=False)

    def __str__(self):
        # return f"{self.user.username} {self.action} "
        return f"{self.created_at} - {self.user.username} - {self.action}"



# Site Settings Model========================================
class SignUpSlider(models.Model):
    text = models.TextField(max_length=255)
    photo = models.ImageField(upload_to="slide/signup/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CustomerScreenSlide(models.Model):
    text = models.TextField(max_length=255)
    photo = models.ImageField(upload_to="slide/customer-screen/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

