from django.db import models
from account.models import User, CustomerProfile, ServiceProviderProfile
from find_worker_config.model_choice import ServiceTaskStatus, ServicePrototypeStatus, JobRequestStatus, OrderStatus, OrderRequestStatus

class ServiceCategory(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Order(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="orders_as_customer")
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="orders_as_provider", blank=True, null=True)
    # customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders_as_customer")
    # provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders_as_provider", blank=True, null=True)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    area = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    service_data = models.DateTimeField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

class OrderRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_requests", blank=True, null=True)
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="provider_order")
    message = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderRequestStatus.choices, default=OrderRequestStatus.PENDING)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

# class ServiceTask(models.Model):
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
#     category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="tasks")
#     title = models.CharField(max_length=255)
#     description = models.TextField()

#     area = models.CharField(max_length=255)
#     lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
#     lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

#     budget_min = models.DecimalField(max_digits=10, decimal_places=2)
#     budget_max = models.DecimalField(max_digits=10, decimal_places=2)

#     status = models.CharField(max_length=50, choices=ServiceTaskStatus.choices, default=ServiceTaskStatus.PENDING)
#     updated_at = models.DateTimeField(auto_now=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title

# class ServicePrototype(models.Model):
#     service_provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prototypes")
#     category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="prototypes")
#     title = models.CharField(max_length=255)
#     description = models.TextField()

#     budget_min = models.DecimalField(max_digits=10, decimal_places=2)
#     budget_max = models.DecimalField(max_digits=10, decimal_places=2)

#     status = models.CharField(max_length=50, choices=ServicePrototypeStatus.choices, default=ServicePrototypeStatus.PENDING)
#     updated_at = models.DateTimeField(auto_now=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.title

# class TaskRequest(models.Model):
#     task = models.ForeignKey(ServiceTask, on_delete=models.CASCADE, related_name="requests")
#     provider = models.ForeignKey(User, on_delete=models.CASCADE)
#     message = models.TextField(blank=True)
#     budget = models.DecimalField(max_digits=10, decimal_places=2)
#     status = models.CharField(max_length=20, choices=JobRequestStatus.choices, default=JobRequestStatus.PENDING)
#     updated_at = models.DateTimeField(auto_now=True)
#     created_at = models.DateTimeField(auto_now_add=True)



