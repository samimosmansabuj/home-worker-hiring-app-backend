from django.db import transaction
from .models import Order, AdminWallet, PaymentTransaction
from find_worker_config.model_choice import OrderStatus, RefundStatus, PaymentTransactionType, PaymentAction, OrderPaymentStatus
from django.utils import timezone

class OrderService:
    @staticmethod
    def accept_order(order, order_request, amount):
        try:
            with transaction.atomic():
                order.provider = order_request.provider
                order.amount = amount
                order.status = OrderStatus.ACCEPT
                order.save(update_fields=["status", "provider", "amount"])


        except Exception as e:
            raise Exception("Order Request not Acceptable.")

def process_refund(refund_obj, admin_user):
    if refund_obj.status != RefundStatus.APPROVED:
        return

    with transaction.atomic():
        wallet = AdminWallet.objects.first()

        wallet.current_balance -= refund_obj.refund_amount
        wallet.save()

        PaymentTransaction.objects.create(
            user=refund_obj.customer.user,
            amount=refund_obj.refund_amount,
            type=PaymentTransactionType.DEBIT,
            action=PaymentAction.REFUND_CUSTOMER,
            reference=f"Refund for Order {refund_obj.order.id}",
            service=refund_obj.order
        )

        refund_obj.status = RefundStatus.COMPLETED
        refund_obj.processed_by = admin_user
        refund_obj.processed_at = timezone.now()
        refund_obj.save()

        refund_obj.order.payment_status = OrderPaymentStatus.REFUND
        refund_obj.order.save()
