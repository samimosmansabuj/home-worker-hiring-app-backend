from django.db import models
from account.models import User
# from task.models import ServiceTask
from find_worker_config.model_choice import OrderStatus


# class Order(models.Model):
#     task = models.OneToOneField(ServiceTask, on_delete=models.CASCADE)
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders_as_customer")
#     provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders_as_provider")

#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.CREATED)

#     updated_at = models.DateTimeField(auto_now=True)
#     created_at = models.DateTimeField(auto_now_add=True)

