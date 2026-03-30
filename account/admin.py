from django.contrib import admin
from .models import User, CustomerProfile, ServiceProviderProfile, Address, OTP, ActivityLog, ProviderVerification, Referral, Voucher, CustomerPaymentMethod, ProviderPayoutMethod

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
