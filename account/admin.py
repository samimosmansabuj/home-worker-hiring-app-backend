from django.contrib import admin
from .models import User, CustomerProfile, ServiceProviderProfile, Address, OTP, ActivityLog, ProviderVerification, Referral, Voucher, CustomerPaymentMethod, ProviderPayoutMethod
from unfold.admin import ModelAdmin
from django.contrib import admin

# @admin.register(User)
# class UserAdmin(ModelAdmin):
#     list_display = ("id", "email", "role", "status", "is_active", "is_staff")
#     list_filter = ("role", "status", "is_active")
#     search_fields = ("email", "phone", "username")

#     readonly_fields = ("referral_code", "date_joined")

#     list_select_related = ()

#     actions = ["activate_users", "deactivate_users"]

#     @admin.action(description="Activate selected users")
#     def activate_users(self, request, queryset):
#         queryset.update(is_active=True)

#     @admin.action(description="Deactivate selected users")
#     def deactivate_users(self, request, queryset):
#         queryset.update(is_active=False)


# @admin.register(ServiceProviderProfile)
# class ProviderAdmin(ModelAdmin):
#     list_display = ("user", "is_verified", "availability_status", "rating", "total_jobs")
#     list_filter = ("is_verified", "availability_status")
#     search_fields = ("user__email",)

#     list_select_related = ("user",)

#     actions = ["verify_providers"]

#     @admin.action(description="Verify providers")
#     def verify_providers(self, request, queryset):
#         queryset.update(is_verified=True)


admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(ServiceProviderProfile)
admin.site.register(Address)
admin.site.register(OTP)
admin.site.register(ActivityLog)
admin.site.register(ProviderVerification)
admin.site.register(Referral)
admin.site.register(Voucher)
admin.site.register(CustomerPaymentMethod)
admin.site.register(ProviderPayoutMethod)

