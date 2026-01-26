from django.db import models
from account.models import User
from find_worker_config.model_choice import WalletTransactionType, PaymentTransactionType, PaymentCurrencyType, PaymentAction
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# class Wallet(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     total_withdraw = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     total_hold = models.DecimalField(max_digits=12, decimal_places=2, default=0)


# class WalletTransaction(models.Model):
#     wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
#     amount = models.DecimalField(max_digits=12, decimal_places=2)
#     type = models.CharField(max_length=10, choices=WalletTransactionType.choices)
#     reference = models.CharField(max_length=100)
#     created_at = models.DateTimeField(auto_now_add=True)

class AdminWallet(models.Model):
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hold_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Current Balance: {self.current_balance} | Hold Balance: {self.hold_balance} | Total Withdraw: {self.total_withdraw}"

class PaymentTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=20, choices=PaymentCurrencyType.choices, default=PaymentCurrencyType.CA)
    type = models.CharField(max_length=20, choices=PaymentTransactionType.choices)
    payment_method_information = models.JSONField(blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=50, choices=PaymentAction.choices, blank=True, null=True)
    # reference object------
    entity_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    entity_id = models.PositiveBigIntegerField()
    service = GenericForeignKey('entity_type', 'entity_id')

    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.amount} Doller Payment {self.user.first_name} For {type}"


