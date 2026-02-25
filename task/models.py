from django.db import models
from account.models import User, CustomerProfile, ServiceProviderProfile
from find_worker_config.model_choice import ServiceTaskStatus, ServicePrototypeStatus, JobRequestStatus, OrderStatus, OrderRequestStatus, ReviewRatingChoice, OrderPaymentStatus, PaymentCurrencyType, PaymentTransactionType, PaymentAction
from django.db import transaction
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import secrets
import string

class ServiceCategory(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class ServiceSubCategory(models.Model):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} of {self.category.title}"

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
        "task.PaymentTransaction",
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
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="order_review")
    customer = models.ForeignKey(CustomerProfile, on_delete=models.SET_NULL, blank=True, null=True)
    provider = models.ForeignKey(ServiceProviderProfile, on_delete=models.SET_NULL, blank=True, null=True)
    rating = models.IntegerField(choices=ReviewRatingChoice.choices, default=ReviewRatingChoice.FIVE)
    review = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now=True)



# ==========================================================================================
# ============= Payment transaction & Wallet Section Start=============================
class AdminWallet(models.Model):
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hold_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment Balance: {self.payment_balance} | Current Balance: {self.current_balance} | Hold Balance: {self.hold_balance} | Total Withdraw: {self.total_withdraw}"




class PaymentTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    payment_id = models.CharField(max_length=50, blank=True, null=True, unique=True, editable=False)
    transaction_id = models.CharField(max_length=50, blank=True, null=True, unique=True, editable=False)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=20, choices=PaymentCurrencyType.choices, default=PaymentCurrencyType.CA)
    type = models.CharField(max_length=20, choices=PaymentTransactionType.choices)
    payment_information = models.JSONField(blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=50, choices=PaymentAction.choices, blank=True, null=True)
    # reference object------
    entity_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    entity_id = models.PositiveBigIntegerField()
    service = GenericForeignKey('entity_type', 'entity_id')

    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def generate_payment_id(self):
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(chars) for _ in range(6))
            generate_id = f"PAY-{code}"
            if not PaymentTransaction.objects.filter(payment_id=generate_id).exists():
                return generate_id
            

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = self.generate_payment_id()
        return super().save(*args, **kwargs)

    # def __str__(self):
    #     return f"{self.amount} Doller Payment {self.user.first_name} For {self.action} | Payment Type {self.type}"
    def __str__(self):
        return f"{self.payment_id} | {self.amount} | {self.action}"

# ============= Payment transaction & Wallet Section End=============================
# ==========================================================================================

