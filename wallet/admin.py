from django.contrib import admin
# from .models import Wallet, WalletTransaction
from .models import AdminWallet, PaymentTransaction

admin.site.register(AdminWallet)
admin.site.register(PaymentTransaction)
# admin.site.register(Wallet)
# admin.site.register(WalletTransaction)
