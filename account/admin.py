from .models import User, CustomerProfile, ServiceProviderProfile, Address, OTP, ActivityLog, ProviderVerification, Referral, Voucher, CustomerPaymentMethod, ProviderPayoutMethod, HelperStrike, HelperWeeklyAvailability, HelperSpecialDate, HelperSlotException, HelperWallet, SavedHelper
# from unfold.admin import ModelAdmin

from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils.html import format_html
from .adminInline import AddressInline, SavedHelperInline, WalletInline, WeeklyAvailabilityInline, CustomerPaymentInline, ProviderPayoutInline


@admin.register(User)
class UserAdmin(ModelAdmin):
    list_display = (
        "id",
        "profile_image",
        "full_name",
        "email",
        "phone",
        "role",
        "status",
        "is_verified",
        "date_joined",
    )

    search_fields = (
        "email",
        "phone",
        "username",
        "first_name",
        "last_name",
    )

    list_filter = (
        "role",
        "status",
        "is_active",
        "is_email_verified",
        "is_phone_verified",
    )

    readonly_fields = (
        "date_joined",
        "updated_at",
        "last_login",
        "referral_code",
    )

    list_per_page = 30

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "photo",
                    "first_name",
                    "last_name",
                    "username",
                    "email",
                    "phone",
                )
            }
        ),

        (
            "Account Settings",
            {
                "fields": (
                    "role",
                    "status",
                    "default_profile",
                )
            }
        ),

        (
            "Verification",
            {
                "fields": (
                    "is_email_verified",
                    "is_phone_verified",
                )
            }
        ),

        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            }
        ),

        (
            "System Information",
            {
                "fields": (
                    "referral_code",
                    "last_login",
                    "date_joined",
                    "updated_at",
                )
            }
        ),
    )

    inlines = [AddressInline]
    
    @admin.display(description="Photo")
    def profile_image(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="40" height="40" style="border-radius:50%;" />',
                obj.photo.url
            )
        return "-"
    
    @admin.display(boolean=True)
    def is_verified(self, obj):
        return obj.is_email_verified or obj.is_phone_verified

@admin.register(CustomerProfile)
class CustomerProfileAdmin(ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "rating",
        "total_orders",
        "completed_orders",
        "completion_rate",
        "total_spent",
        "is_verified",
        "is_blocked",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__phone",
    )

    list_filter = (
        "is_verified",
        "is_blocked",
    )

    readonly_fields = (
        "completion_rate",
        "created_at",
        "updated_at",
    )

    autocomplete_fields = ("user",)
    
    inlines = [
        SavedHelperInline
    ]

    @admin.display(description="Customer")
    def customer_name(self, obj):
        return obj.user.full_name or obj.user.username

# ----------------------Provider Helper------------------
@admin.register(ServiceProviderProfile)
class ServiceProviderAdmin(ModelAdmin):

    list_display = (
        "id",
        "provider_name",
        "company_name",
        "rating",
        "total_jobs",
        "complete_rate",
        "is_verified",
        "availability_status",
        "account_status",
    )

    search_fields = (
        "user__username",
        "user__email",
        "company_name",
        "user__phone",
    )

    list_filter = (
        "is_verified",
        "availability_status",
        "account_status",
        "service_category",
    )

    readonly_fields = (
        "rating",
        "total_jobs",
        "complete_rate",
        "total_profile_view",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Provider Identity", {
            "fields": (
                "user",
                "company_name",
                "logo",
                "details",
                "office_location",
            )
        }),

        ("Service Info", {
            "fields": (
                "service_category",
                "hourly_rate",
                "min_booking_hours",
            )
        }),

        ("Status", {
            "fields": (
                "account_status",
                "availability_status",
                "is_verified",
                "strike_count",
            )
        }),

        ("Analytics", {
            "fields": (
                "rating",
                "total_jobs",
                "complete_rate",
                "total_profile_view",
            )
        }),
    )

    inlines = [
        WalletInline,
        WeeklyAvailabilityInline, ProviderPayoutInline
    ]

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.user.full_name or obj.user.username

# @admin.register(HelperWallet)
# class HelperWalletAdmin(ModelAdmin):

#     list_display = (
#         "id",
#         "provider_name",
#         "total_payout",
#         "available_payout",
#         "upcoming_payout",
#         "payout_processing",
#     )

#     search_fields = (
#         "provider__user__username",
#         "provider__user__email",
#     )

#     autocomplete_fields = ("provider",)

#     readonly_fields = (
#         "total_payout",
#         "available_payout",
#         "upcoming_payout",
#         "payout_processing",
#         "update_at",
#     )

#     @admin.display(description="Provider")
#     def provider_name(self, obj):
#         return obj.provider.user.username

# @admin.register(HelperWeeklyAvailability)
# class WeeklyAvailabilityAdmin(ModelAdmin):
#     list_display = (
#         "id",
#         "provider_name",
#         "day",
#         "day_status",
#         "start_time",
#         "end_time",
#         "slot_duration_minutes",
#     )

#     list_filter = (
#         "day",
#         "day_status",
#     )

#     search_fields = (
#         "provider__user__username",
#         "provider__user__email",
#     )

#     autocomplete_fields = ("provider",)

#     @admin.display(description="Provider")
#     def provider_name(self, obj):
#         return obj.provider.user.username

@admin.register(HelperStrike)
class StrikeAdmin(ModelAdmin):
    list_display = (
        "id",
        "provider_name",
        "reason",
        "is_active",
        "expires_at",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "provider__user__username",
        "reason",
    )

    autocomplete_fields = ("provider",)

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username

@admin.register(HelperSpecialDate)
class SpecialDateAdmin(ModelAdmin):
    list_display = (
        "id",
        "provider_name",
        "date",
        "date_status",
        "start_time",
        "end_time",
    )

    list_filter = (
        "date_status",
        "date",
    )

    autocomplete_fields = ("provider",)

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username

@admin.register(HelperSlotException)
class SlotExceptionAdmin(ModelAdmin):
    list_display = (
        "id",
        "provider_name",
        "type",
        "date",
        "start_time",
        "end_time",
        "is_active",
    )

    list_filter = (
        "type",
        "date",
        "is_active",
    )

    search_fields = (
        "provider__user__username",
    )

    # autocomplete_fields = (
    #     "provider",
    #     "order",
    # )

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username

# ----------------------Provider Helper------------------

@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_name",
        "address_line",
        "city",
        "is_default",
        "lat",
        "lng",
    )

    search_fields = (
        "user__username",
        "user__email",
        "city",
        "address_line",
    )

    list_filter = (
        "is_default",
        "city",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "get_address",
    )

    fieldsets = (
        ("User Info", {
            "fields": (
                "user",
                "is_default",
            )
        }),

        ("Address Info", {
            "fields": (
                "address_line",
                "city",
                "lat",
                "lng",
            )
        }),

        ("System", {
            "fields": (
                "get_address",
            )
        }),
    )

    @admin.display(description="User")
    def user_name(self, obj):
        return obj.user.username

@admin.register(SavedHelper)
class SavedHelperAdmin(ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "helper_name",
        "created_at",
    )

    search_fields = (
        "customer__user__username",
        "customer__user__email",
        "helper__user__username",
        "helper__user__email",
    )

    list_filter = (
        "created_at",
    )

    autocomplete_fields = (
        "customer",
        "helper",
    )

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        ("Relationship", {
            "fields": (
                "customer",
                "helper",
            )
        }),

        ("Meta", {
            "fields": (
                "created_at",
            )
        }),
    )

    @admin.display(description="Customer")
    def customer_name(self, obj):
        return obj.customer.user.username

    @admin.display(description="Helper")
    def helper_name(self, obj):
        return obj.helper.user.username

@admin.register(CustomerPaymentMethod)
class CustomerPaymentMethodAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_name",
        "provider",
        "method_type",
        "brand",
        "last4",
        "is_default",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "provider",
        "last4",
    )

    list_filter = (
        "provider",
        "method_type",
        "is_default",
        "created_at",
    )

    autocomplete_fields = ("user",)

    readonly_fields = (
        "payment_token",
        "created_at",
    )

    fieldsets = (
        ("User Info", {
            "fields": (
                "user",
                "is_default",
            )
        }),

        ("Payment Method", {
            "fields": (
                "provider",
                "method_type",
                "brand",
                "last4",
            )
        }),

        ("Secure Data", {
            "fields": (
                "payment_token",
                "method_data",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
            )
        }),
    )

    @admin.display(description="User")
    def user_name(self, obj):
        return obj.user.username

@admin.register(ProviderPayoutMethod)
class ProviderPayoutMethodAdmin(ModelAdmin):
    list_display = (
        "id",
        "provider_name",
        "method_type",
        "account_holder_name",
        "bank_name",
        "paypal_email",
        "is_verified",
        "is_default",
        "created_at",
    )

    search_fields = (
        "provider__user__username",
        "provider__user__email",
        "account_holder_name",
        "paypal_email",
    )

    list_filter = (
        "method_type",
        "is_verified",
        "is_default",
        "created_at",
    )

    autocomplete_fields = ("provider",)

    readonly_fields = (
        "account_token",
        "created_at",
    )

    fieldsets = (
        ("Provider Info", {
            "fields": (
                "provider",
                "is_default",
                "is_verified",
            )
        }),

        ("Payout Method", {
            "fields": (
                "method_type",
                "account_holder_name",
                "bank_name",
                "account_number",
                "ifsc_code",
                "paypal_email",
            )
        }),

        ("Secure Data", {
            "fields": (
                "account_token",
                "method_data",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
            )
        }),
    )

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username


@admin.register(OTP)
class OTPAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_name",
        "phone",
        "email",
        "purpose",
        "code",
        "is_used",
        "is_expired_display",
        "created_at",
    )

    search_fields = (
        "phone",
        "email",
        "user__username",
        "code",
    )

    list_filter = (
        "purpose",
        "is_used",
        "created_at",
    )

    readonly_fields = (
        "code",
        "created_at",
        "is_expired_display",
    )

    fieldsets = (
        ("User Info", {
            "fields": (
                "user",
                "phone",
                "email",
            )
        }),

        ("OTP Info", {
            "fields": (
                "purpose",
                "code",
                "is_used",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
                "is_expired_display",
            )
        }),
    )

    @admin.display(description="User")
    def user_name(self, obj):
        return obj.user.username if obj.user else "-"

    @admin.display(boolean=True, description="Expired")
    def is_expired_display(self, obj):
        return obj.is_expired()

@admin.register(ProviderVerification)
class ProviderVerificationAdmin(ModelAdmin):
    list_display = (
        "id",
        "provider_name",
        "full_name",
        "document_type",
        "status",
        "is_verified",
        "update_at",
    )

    search_fields = (
        "provider__user__username",
        "provider__user__email",
        "full_name",
        "document_id",
        "dob",
        "document_type"
    )

    list_filter = (
        "status",
        "is_verified",
        "document_type",
        "dob",
    )

    autocomplete_fields = ("provider",)

    readonly_fields = ("update_at",)

    fieldsets = (
        ("Provider Info", {
            "fields": (
                "provider",
            )
        }),

        ("Document", {
            "fields": (
                "document_type",
                "document",
                "full_name",
                "dob",
                "document_id"
            )
        }),

        ("Verification Status", {
            "fields": (
                "is_verified",
                "status",
            )
        }),

        ("System", {
            "fields": (
                "update_at",
            )
        }),
    )

    @admin.display(description="Provider")
    def provider_name(self, obj):
        return obj.provider.user.username


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = (
        "id",
        "referrer_name",
        "referred_name",
        "code",
        "reward_given",
        "created_at",
    )

    search_fields = (
        "referrer__username",
        "referred__username",
        "code",
    )

    list_filter = (
        "reward_given",
        "created_at",
    )

    readonly_fields = ("created_at",)

    @admin.display(description="Referrer")
    def referrer_name(self, obj):
        return obj.referrer.username

    @admin.display(description="Referred")
    def referred_name(self, obj):
        return obj.referred.username

@admin.register(Voucher)
class VoucherAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "voucher_type",
        "discount_type",
        "value",
        "is_used",
        "is_active",
        "expiry_date",
    )

    search_fields = (
        "code",
        "name",
        "user__username",
    )

    list_filter = (
        "voucher_type",
        "discount_type",
        "is_used",
        "is_active",
    )

    autocomplete_fields = ("user",)

    readonly_fields = ("created_at",)

    fieldsets = (
        ("Voucher Info", {
            "fields": (
                "name",
                "code",
                "voucher_type",
                "user",
            )
        }),

        ("Discount Info", {
            "fields": (
                "discount_type",
                "value",
                "minimum_value",
                "upto_value",
            )
        }),

        ("Status", {
            "fields": (
                "is_used",
                "is_active",
                "expiry_date",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
            )
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(ModelAdmin):
    list_display = (
        "id",
        "user_name",
        "user_type",
        "action",
        "status",
        "ip_address",
        "need_notify",
        "created_at",
    )

    search_fields = (
        "user__username",
        "action",
        "message",
        "ip_address",
    )

    list_filter = (
        "status",
        "user_type",
        "need_notify",
        "created_at",
    )

    readonly_fields = (
        "user",
        "user_type",
        "action",
        "message",
        "status",
        "entity_type",
        "entity_id",
        "ip_address",
        "created_at",
    )

    date_hierarchy = "created_at"

    fieldsets = (
        ("User Info", {
            "fields": (
                "user",
                "user_type",
            )
        }),

        ("Activity Details", {
            "fields": (
                "action",
                "message",
                "status",
            )
        }),

        ("Related Object", {
            "fields": (
                "entity_type",
                "entity_id",
            )
        }),

        ("Security Info", {
            "fields": (
                "ip_address",
                "need_notify",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
            )
        }),
    )

    @admin.display(description="User")
    def user_name(self, obj):
        return obj.user.username if obj.user else "-"

