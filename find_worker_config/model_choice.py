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
    SUN = "Sun", "Sunday"
    MON = "Mon", "Monday"
    TUE = "Tue", "Tuesday"
    WED = "Wed", "Wednesday"
    THU = "Thu", "Thursday"
    FRI = "Fri", "Friday"
    SAT = "Sat", "Saturday"

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
    CANCELLATION_REQUEST = "CANCELLATION_REQUEST"
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

class OrderChangeRequestAction(models.TextChoices):
    PROVIDER_TIME_CHANGE_REQUEST_SEND = "PROVIDER_TIME_CHANGE_REQUEST_SEND"
    CUSTOMER_TIME_CHANGE_REQUEST_SEND = "CUSTOMER_TIME_CHANGE_REQUEST_SEND"
    PROVIDER_COUNTER_SEND = "PROVIDER_COUNTER_SEND"
    CUSTOMER_COUNTER_SEND = "CUSTOMER_COUNTER_SEND"
    PROVIDER_CANCEL_REQUEST_SEND = "PROVIDER_CANCEL_REQUEST_SEND"
    CUSTOMER_CANCEL_REQUEST_SEND = "CUSTOMER_CANCEL_REQUEST_SEND"
    NO_ACTION = "NO_ACTION"

class ChangesRequestType(models.TextChoices):
    TIME = "TIME"
    DATE = "DATE"
    TIME_AND_DATE = "TIME_AND_DATE"
    AMOUNT = "AMOUNT"
    COUNTER = "COUNTER"
    SET_HOUR = "SET_HOUR"
    CANCEL = "CANCEL"

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
    TEXT = "TEXT", "Text"
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    AUDIO = "AUDIO"
    FILE = "FILE", "File"
    EVENT = "EVENT", "event"

class SendEventType(models.TextChoices):
    ORDER_CREATED = "ORDER_CREATED", "Order Created"
    ORDER_COUNTER = "ORDER_COUNTER", "Order Counter"
    ORDER_UPDATED = "ORDER_UPDATED", "Order Updated"
    ORDER_STATUS = "ORDER_STATUS", "Order Status"
    ORDER_CANCEL = "ORDER_CANCEL", "Order Cancel"
    ORDER_COMPLETE = "ORDER_COMPLETEL", "Order Complete"
    ORDER_WORK_START = "ORDER_WORK_START", "Order Work Start"
    ORDER_HOUR_SET = "ORDER_HOUR_SET", "Order Hour Set"
    ORDER_CHANGE_REQUEST = "ORDER_CHANGE_REQUEST", "Order Change Request"


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

class MailConfigType(models.TextChoices):
    SMTP = "smtp"
    API = "api"



# ==================================================================================
# ==================================================================================
class LogStatus(models.TextChoices):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"



