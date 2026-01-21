from django.db import models
from django.utils.translation import gettext_lazy as _

# For Account App================================================
class UserRole(models.TextChoices):
    USER = "USER", _("User")
    ADMIN = "ADMIN", _("Administrator")

class UserDefault(models.TextChoices):
    CUSTOMER = "CUSTOMER", _("Customer")
    PROVIDER = "PROVIDER", _("Provider")

class UserLanguage(models.TextChoices):
    EN = "English"
    ZH = "Chinese"

class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    DEACTIVE = "DEACTIVE"
    REJECTED = "REJECTED"

class PaymentMethodType(models.TextChoices):
    CARD = "CARD"
    BANK = "BANK"
    WALLET = "WALLET"

class OTPType(models.TextChoices):
    LOGIN = "LOGIN"
    SIGNUP = "SIGNUP"
    VERIFY = "VERIFY"


# For Task App===================================================
class ServiceTaskStatus(models.TextChoices):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    HIRED = "HIRED"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class ServicePrototypeStatus(models.TextChoices):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    HIRED = "HIRED"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class JobRequestStatus(models.TextChoices):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class OrderRequestStatus(models.TextChoices):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class OrderStatus(models.TextChoices):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ACCEPT = "ACCEPT"
    HIRIED = "HIRIED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_COMPLETE = "PARTIAL_COMPLETE"
    CANCELLED = "CANCELLED"
    REFUND = "REFUND"
    


# For Order App=====================================================
class OrderStatusOld(models.TextChoices):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# For Wallet App===================================================
class WalletTransactionType(models.TextChoices):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    HOLD = "HOLD"


# For Chat & Notify App============================================
class SendMessageType(models.TextChoices):
    TEXT = "Text"
    IMAGE = "Image"
    VIDEO = "Video"
    AUDIO = "Audio"
    FILE  = "File"
    OFFER = "Offer"

class CustomOfferStatus(models.TextChoices):
    SEND = "SEND"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELED = "CANCELED"

class NotifyType(models.TextChoices):
    GET = "GET"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


