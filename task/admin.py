from django.contrib import admin
# from .models import ServiceCategory, ServiceTask, ServicePrototype, TaskRequest
from .models import ServiceCategory, Order, OrderRequest

admin.site.register(ServiceCategory)
admin.site.register(Order)
admin.site.register(OrderRequest)
# admin.site.register(ServiceTask)
# admin.site.register(ServicePrototype)
# admin.site.register(TaskRequest)
