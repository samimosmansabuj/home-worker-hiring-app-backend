import django_filters
from task.models import PaymentTransaction, OrderRefundRequest, Order
from find_worker_config.model_choice import OrderPaymentStatus, OrderStatus
from django.db.models import Q


class PaymentTransactionFilter(django_filters.FilterSet):
    type = django_filters.CharFilter(field_name="type")

    class Meta:
        model = PaymentTransaction
        fields = ["type"]

class OrderRefundFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")

    class Meta:
        model = OrderRefundRequest
        fields = ["status"]

class OrderFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")

    class Meta:
        model = Order
        fields = ["status"]

    def filter_status(self, queryset, name, value):
        value = value.upper()
        if value == "PENDING":
            return queryset.filter(
                status=OrderStatus.PENDING
            )
        elif value == "ACCEPT":
            return queryset.filter(
                status=OrderStatus.ACCEPT
            )
        elif value == "CONFIRM":
            return queryset.filter(
                status=OrderStatus.CONFIRM
            )
        elif value == "IN_PROGRESS":
            return queryset.filter(
                status=OrderStatus.IN_PROGRESS
            )
        elif value == "COMPLETE":
            return queryset.filter(
                status=OrderStatus.COMPLETED
            )
        elif value == "DISBURSE":
            return queryset.filter(
                status=OrderStatus.COMPLETED,
                payment_status=OrderPaymentStatus.DISBURSEMENT
            )
        elif value == "CANCEL":
            return queryset.filter(
                Q(status=OrderStatus.CANCELLED) |
                Q(status=OrderStatus.CANCELLATION_REQUEST)
            )
        elif value == "REFUND":
            return queryset.filter(
                Q(status=OrderStatus.REFUND) |
                Q(status=OrderStatus.REFUND_REQUEST)
            )
        return queryset
