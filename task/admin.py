from django.contrib import admin
# from .models import ServiceCategory, ServiceTask, ServicePrototype, TaskRequest
from .models import ServiceCategory, Order, OrderRequest, ReviewAndRating, AdminWallet, PaymentTransaction, OrderRefundRequest

admin.site.register(ServiceCategory)
admin.site.register(Order)
admin.site.register(OrderRequest)
admin.site.register(ReviewAndRating)
admin.site.register(AdminWallet)
admin.site.register(PaymentTransaction)
admin.site.register(OrderRefundRequest)

