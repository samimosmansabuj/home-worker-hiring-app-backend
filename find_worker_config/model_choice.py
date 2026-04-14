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
    EN = "en"
    ZH = "zh"

class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    DEACTIVE = "DEACTIVE"
    REJECTED = "REJECTED"

class HelperStatus(models.TextChoices):
    GOOD = "GOOD"
    WARNING = "WARNING"
    DANGER = "DANGER"
    TEMPORARY_SUSPENSED = "TEMPORARY_SUSPENSED"
    PERMANENT_SUSPENSED = "PERMANENT_SUSPENSED"

class WeekDay(models.TextChoices):
    MON = "mon", "Monday"
    TUE = "tue", "Tuesday"
    WED = "wed", "Wednesday"
    THU = "thu", "Thursday"
    FRI = "fri", "Friday"
    SAT = "sat", "Saturday"
    SUN = "sun", "Sunday"

class DayStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE"
    OFF = "OFF"
    UNAVAILABLE = "UNAVAILABLE"

class DateStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"

class HelperSlotExceptionType(models.TextChoices):
    BOOKED = "BOOKED"
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE = "AVAILABLE"
    FREEZED = "FREEZED"


class PaymentMethodType(models.TextChoices):
    CARD = "CARD"
    BANK = "BANK"
    WALLET = "WALLET"

class PayoutMethodType(models.TextChoices):
    BANK = "BANK"
    WALLET = "WALLET"

class OTPType(models.TextChoices):
    LOGIN = "LOGIN"
    SIGNUP = "SIGNUP"
    VERIFY = "VERIFY"
    RESET_PASSWORD = "RESET_PASSWORD"

class DocumentType(models.TextChoices):
    PASSPORT = "PASSPORT"
    NID = "NID"
    DRIVING_LICENSE = "DRIVING_LICENSE"

class DocumentStatus(models.TextChoices):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

class VOUCHER_DISCOUNT_TYPE(models.TextChoices):
    PERCENTAGE = "PERCENTAGE"
    FLAT = "FLAT"

class VOUCHER_TYPE(models.TextChoices):
    FOR_USER = "FOR_USER"
    FOR_GLOBAL = "FOR_GLOBAL"

# For Account App================================================


# For Task App===================================================
class OrderStatus(models.TextChoices):
    PENDING = "PENDING"
    ACCEPT = "ACCEPT"
    CONFIRM = "CONFIRM"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIAL_COMPLETE = "PARTIAL_COMPLETE"
    CANCELLED = "CANCELLED"
    REFUND_REQUEST = "REFUND_REQUEST"
    REFUND = "REFUND"

class OrderPaymentStatus(models.TextChoices):
    UNPAID = "UNPAID"
    PAID = "PAID"
    DISBURSEMENT = "DISBURSEMENT"
    CANCELLED = "CANCELLED"
    REFUND = "REFUND"

class OrderChangesRequestStatus(models.TextChoices):
    ACCEPT = "ACCEPT"
    DECLINED = "DECLINED"
    NO_RESPONSE = "NO_RESPONSE"

class ChangesRequestType(models.TextChoices):
    TIME = "TIME"
    DATE = "DATE"
    TIME_AND_DATE = "TIME_AND_DATE"
    AMOUNT = "AMOUNT"
    COUNTER = "COUNTER"
    SET_HOUR = "SET_HOUR"

class ReviewRatingChoice(models.IntegerChoices):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

class RefundStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    COMPLETED = "COMPLETED", "Completed"

# For Task App===================================================


# For Wallet App===================================================
class PaymentTransactionType(models.TextChoices):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"
    HOLD = "HOLD"

class PaymentCurrencyType(models.TextChoices):
    CN = "CN¥"
    CA = "CA$"

class PaymentAction(models.TextChoices):
    ORDER_PAYMENT = "ORDER_PAYMENT"
    PAYMENT_HOLD = "PAYMENT_HOLD"
    SEND_PROVIDER = "SEND_PROVIDER"
    REFUND_CUSTOMER = "REFUND_CUSTOMER"

class ServiceChargeType(models.TextChoices):
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"

# For Chat & Notify App============================================
class SendMessageType(models.TextChoices):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE  = "FILE"
    OFFER = "OFFER"

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

# For Chat & Notify App============================================



# For Core App============================================
class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    CLOSED = "closed", "Closed"

class TicketSenderType(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"
    # PROVIDER = "provider", "Provider"

class TicketUserProfileType(models.TextChoices):
    CUSTOMER = "CUSTOMER", _("Customer")
    PROVIDER = "PROVIDER", _("Provider")


