from django.contrib import admin
# from .models import ServiceCategory, ServiceTask, ServicePrototype, TaskRequest
from .models import ServiceCategory, Order, ReviewAndRating, AdminWallet, PaymentTransaction, OrderRefundRequest, OrderChangesRequest

admin.site.register(ServiceCategory)
admin.site.register(Order)
admin.site.register(OrderChangesRequest)
admin.site.register(ReviewAndRating)
admin.site.register(AdminWallet)
admin.site.register(PaymentTransaction)
admin.site.register(OrderRefundRequest)

