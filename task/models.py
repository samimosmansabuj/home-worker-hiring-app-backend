from django.db import models
from account.models import User, CustomerProfile, ServiceProviderProfile
from find_worker_config.model_choice import ServiceTaskStatus, ServicePrototypeStatus, JobRequestStatus, OrderStatus, OrderRequestStatus, ReviewRatingChoice, OrderPaymentStatus
from django.db import transaction
from django.contrib.contenttypes.fields import GenericRelation
from wallet.models import PaymentTransaction

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
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    area = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    budget_min = models.DecimalField(max_digits=10, decimal_places=2)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2)

    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.ACTIVE)
    payment_status = models.CharField(max_length=20, choices=OrderPaymentStatus.choices, default=OrderPaymentStatus.UNPAID)
    service_data = models.DateTimeField(blank=True, null=True)
    confirmation_OTP = models.CharField(max_length=6, blank=True, null=True)

    payment_transactions = GenericRelation(
        PaymentTransaction,
        content_type_field="entity_type",
        object_id_field="entity_id",
        related_query_name="order"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == OrderStatus.ACCEPT and not self.provider:
            raise ValueError("Cannot accept order without provider")
        is_status_changed = False
        if self.pk:
            old_status = Order.objects.get(pk=self.pk).status
            is_status_changed = old_status != self.status
        if self.payment_status == OrderPaymentStatus.PAID and self.status in [OrderStatus.ACCEPT, OrderStatus.ACTIVE]:
            self.status = OrderStatus.CONFIRM
        super().save(*args, **kwargs)

        if (is_status_changed and self.status == OrderStatus.ACCEPT and self.provider):
            with transaction.atomic():
                OrderRequest.objects.filter(
                    order=self,
                    provider=self.provider
                ).update(status=OrderRequestStatus.ACCEPTED)
                OrderRequest.objects.filter(
                    order=self
                ).exclude(
                    provider=self.provider
                ).update(status=OrderRequestStatus.TERMINATE)

        if (is_status_changed and self.status == OrderStatus.ACTIVE and old_status in (OrderStatus.COMPLETED, OrderStatus.ACCEPT)):
            with transaction.atomic():
                OrderRequest.objects.filter(
                    order=self
                ).update(status=OrderRequestStatus.PENDING)

class OrderRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_requests", blank=True, null=True)
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.CASCADE, related_name="provider_order")
    message = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderRequestStatus.choices, default=OrderRequestStatus.PENDING)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ReviewAndRating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="order_reiviews")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.SET_NULL, blank=True, null=True)
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.SET_NULL, blank=True, null=True)
    rating = models.IntegerField(choices=ReviewRatingChoice.choices, default=ReviewRatingChoice.FIVE)
    review = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now=True)

