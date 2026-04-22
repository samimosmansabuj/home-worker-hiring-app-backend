from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from find_worker_config.model_choice import  DateStatus, DayStatus, HelperSlotExceptionType, HelperStatus, UserRole, UserLanguage, UserStatus, PaymentMethodType, PayoutMethodType, OTPType, UserDefault, DocumentType, DocumentStatus, VOUCHER_DISCOUNT_TYPE, VOUCHER_TYPE, WeekDay, LogStatus
from .managers import CustomUserManager
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .utils import generate_otp, image_delete_os, previous_image_delete_os
from django.db import transaction
import random
import string
from encrypted_model_fields.fields import EncryptedCharField
from django.db import transaction
from django.core.exceptions import ValidationError



# Custom User Model====================================
class User(AbstractBaseUser, PermissionsMixin):
    role = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.USER)
    default_profile = models.CharField(max_length=30, choices=UserDefault.choices, blank=True, null=True)
    status = models.CharField(max_length=30, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=255, unique=True, blank=True,  null=True)
    phone = models.CharField(max_length=20, unique=True, blank=True,  null=True)
    photo = models.ImageField(upload_to="user/photo/", blank=True, null=True)
    
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=50, unique=True, blank=True, null=True, editable=False)

    language = models.CharField(max_length=10, choices=UserLanguage.choices, default=UserLanguage.EN)
    timezone = models.CharField(max_length=50, default="UTC")
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone"]

    objects = CustomUserManager()

    @property
    def hasCustomerProfile(self):
        try:
            return self.customer_profile
        except:
            return None
    
    @property
    def hasServiceProviderProfile(self):
        try:
            return self.service_provider_profile
        except:
            return None
    
    def image_update(self, instance):
        previous_image_delete_os(instance.photo, self.photo)
    
    def delete(self, *args, **kwargs):
        image_delete_os(self.photo)
        return super().delete(*args, **kwargs)

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
        username = username.lower()
        if username and User.objects.filter(username=username).exists():
            username = f"{username}{random.randint(1000, 9999)}"
        return username

    def generate_referral_code(self):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while User.objects.filter(referral_code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return code

    def save(self, *args, **kwargs):
        if self.pk and self.photo and User.objects.filter(pk=self.pk).exists():
            instance = User.objects.get(pk=self.pk)
            self.image_update(instance)
        
        if not self.username: self.username = self.generate_username()
        if not self.referral_code: self.referral_code = self.generate_referral_code()

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


# ===================================================================
# Service Provider Profile================================
class ServiceProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="service_provider_profile")
    service_category = models.ManyToManyField("task.ServiceCategory", blank=True)
    # service_subcategory = models.ManyToManyField("task.ServiceSubCategory", blank=True)

    company_name = models.CharField(max_length=100, blank=True, null=True)
    # email = models.EmailField(max_length=255, unique=True, blank=True,  null=True)
    # phone = models.CharField(max_length=20, unique=True, blank=True,  null=True)
    logo = models.ImageField(upload_to="provider/logo/", blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    office_location = models.ForeignKey("account.Address", on_delete=models.DO_NOTHING, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_booking_hours = models.PositiveIntegerField(default=1)

    strike_count = models.PositiveIntegerField(default=0)
    account_status = models.CharField(max_length=20, choices=HelperStatus.choices, default=HelperStatus.GOOD)
    availability_status = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    complete_rate = models.FloatField(default=0)
    total_jobs = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - Provider Profile"

class HelperStrike(models.Model):
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="strikes")
    reason = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class HelperWeeklyAvailability(models.Model):
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="weekly_availability")
    day = models.CharField(max_length=10, choices=WeekDay.choices)
    day_status = models.CharField(max_length=20, choices=DayStatus.choices, default=DayStatus.AVAILABLE)

    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    slot_duration_minutes = models.PositiveIntegerField(default=60)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("provider", "day")    
        indexes = [
            models.Index(fields=["provider", "day"]),
        ]

    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("Invalid time range")

class HelperSpecialDate(models.Model):
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="special_dates")
    date = models.DateField()
    date_status = models.CharField(max_length=20, choices=DateStatus.choices, default=DateStatus.AVAILABLE)
    description = models.CharField(max_length=255, blank=True, null=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Invalid special date time range")
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Invalid exception time range")

class HelperSlotException(models.Model):
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="slot_exceptions")
    type = models.CharField(max_length=20, choices=HelperSlotExceptionType.choices, default=HelperSlotExceptionType.BOOKED)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    order = models.ForeignKey("task.Order", on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Invalid exception time range")


class HelperWallet(models.Model):
    provider = models.OneToOneField(ServiceProviderProfile, on_delete=models.CASCADE, related_name="wallet", blank=True, null=True)
    total_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    upcoming_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payout_processing = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

# ============================Service Provider Profile====================


# Address Model===========================================
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_line = models.CharField(max_length=600, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    lat = models.FloatField(max_length=9, blank=True, null=True)
    lng = models.FloatField(max_length=9, blank=True, null=True)
    is_default = models.BooleanField(default=False)

    @property
    def get_address(self):
        return f"{self.address_line}, {self.city}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.is_default:
                Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
            elif not Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).exists():
                self.is_default = True
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address_line} for {self.user}"
    
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            user = self.user
            was_default = self.is_default
            super().delete(*args, **kwargs)

            if was_default:
                next_address = Address.objects.filter(user=user).first()
                if next_address:
                    next_address.is_default = True
                    next_address.save()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="unique_default_address_per_user"
            )
        ]

    def __str__(self):
        return f"{self.address_line} for {self.user}"

class SavedHelper(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="saved_helpers")
    helper = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="saved_by_customers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "helper")

# ============================Address======================


# Payment Method Model=====================================  
class CustomerPaymentMethod(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_methods")
    provider = models.CharField(max_length=50)  # stripe, razorpay
    method_type = models.CharField(max_length=30, choices=PaymentMethodType.choices)

    payment_token = models.CharField(max_length=255)
    brand = models.CharField(max_length=50, blank=True, null=True)
    last4 = models.CharField(max_length=4, blank=True, null=True)
    # optional extra data (non-sensitive only)
    method_data = models.JSONField(blank=True, null=True)

    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_payment_per_user"
            )
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not CustomerPaymentMethod.objects.filter(user=self.user).exists():
                self.is_default = True
            
            if self.is_default:
                CustomerPaymentMethod.objects.filter(
                    user=self.user,
                    is_default=True
                ).update(is_default=False)
            super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        with transaction.atomic():
            user = self.user
            is_default = self.is_default
            super().delete(*args, **kwargs)
            if is_default:
                next_method = CustomerPaymentMethod.objects.filter(user=user).first()
                if next_method:
                    next_method.is_default = True
                    next_method.save()

class ProviderPayoutMethod(models.Model):
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="payout_methods")
    method_type = models.CharField(max_length=50, choices=PayoutMethodType.choices, default=PayoutMethodType.BANK)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)

    # External account reference (Stripe/PayPal/etc.)
    account_token = models.CharField(max_length=255, blank=True, null=True)
    # BANK
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    # account_number = models.CharField(max_length=255, blank=True, null=True)
    account_number = EncryptedCharField(max_length=255, blank=True, null=True)
    ifsc_code = models.CharField(max_length=50, blank=True, null=True)
    # PAYPAL
    paypal_email = models.EmailField(blank=True, null=True)
    # optional metadata
    method_data = models.JSONField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider"],
                condition=models.Q(is_default=True),
                name="unique_default_payout_per_provider"
            )
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not ProviderPayoutMethod.objects.filter(provider=self.provider).exists():
                self.is_default = True
            
            if self.is_default:
                ProviderPayoutMethod.objects.filter(
                    provider=self.provider,
                    is_default=True
                ).update(is_default=False)
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            provider = self.provider
            is_default = self.is_default
            super().delete(*args, **kwargs)
            if is_default:
                next_method = ProviderPayoutMethod.objects.filter(provider=provider).first()
                if next_method:
                    next_method.is_default = True
                    next_method.save()

# =========================Payment Method===================


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

class ProviderVerification(models.Model):
    provider = models.OneToOneField(ServiceProviderProfile, on_delete=models.CASCADE, related_name="verification")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, blank=True, null=True)
    document = models.ImageField(upload_to="user/verification/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.REVIEW)
    update_at = models.DateTimeField(auto_now=True)

    def image_update(self, instance):
        previous_image_delete_os(instance.document, self.document)
    
    def delete(self, *args, **kwargs):
        image_delete_os(self.document)
        return super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if self.pk and ProviderVerification.objects.filter(pk=self.pk).exists():
            instance = ProviderVerification.objects.get(pk=self.pk)
            self.image_update(instance)
        
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.provider.user.first_name} {self.provider.user.last_name} Provider Profile is Verified: {self.is_verified}"



# Logs Model==============================================
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=30, choices=UserDefault.choices, blank=True, null=True)
    action = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=LogStatus.choices, default=LogStatus.SUCCESS)

    entity_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    entity_id = models.PositiveBigIntegerField(blank=True, null=True)
    service = GenericForeignKey('entity_type', 'entity_id')
    
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)
    need_notify = models.BooleanField(default=False)

    def __str__(self):
        # return f"{self.user.username} {self.action} "
        username = self.user.username if self.user else None
        return f"{self.created_at} - {username} - {self.action}"


# Referral & Vouchar Model========================================
class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrer')
    referred = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referred')
    code = models.CharField(max_length=50)
    reward_given = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Voucher(models.Model):
    voucher_type = models.CharField(max_length=20, choices=VOUCHER_TYPE.choices, default=VOUCHER_TYPE.FOR_GLOBAL)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vouchers", blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True, default="DISCOUNT VOUCHER")
    code = models.CharField(max_length=50)
    discount_type = models.CharField(max_length=20, choices=VOUCHER_DISCOUNT_TYPE.choices, default=VOUCHER_DISCOUNT_TYPE.PERCENTAGE)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    minimum_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    upto_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    is_used = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code}) for {self.voucher_type}"

    def generate_redeem_code(self):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Voucher.objects.filter(code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return code

    def save(self, *args, **kwargs):
        if not self.code: self.code = self.generate_redeem_code()
        return super().save(*args, **kwargs)

