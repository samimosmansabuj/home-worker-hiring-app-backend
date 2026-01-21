from django.db import models
from account.models import User
from find_worker_config.model_choice import WalletTransactionType


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_hold = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class WalletTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=WalletTransactionType.choices)
    reference = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

