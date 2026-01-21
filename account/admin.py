from django.contrib import admin
from .models import User, CustomerProfile, ServiceProviderProfile, Address, PaymentMethod, OTP, ActivityLog

admin.site.register(User)
admin.site.register(CustomerProfile)
admin.site.register(ServiceProviderProfile)
admin.site.register(Address)
admin.site.register(PaymentMethod)
admin.site.register(OTP)
admin.site.register(ActivityLog)
