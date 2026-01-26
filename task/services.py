from django.db import transaction
from .models import OrderRequest, Order
from find_worker_config.model_choice import OrderStatus, OrderRequestStatus

class OrderService:
    @staticmethod
    def accept_order(order, order_request, amount):
        try:
            with transaction.atomic():
                order.provider = order_request.provider
                order.amount = amount
                order.status = OrderStatus.ACCEPT
                order.save(update_fields=["status", "provider", "amount"])

                OrderRequest.objects.filter(
                    order=order
                ).exclude(
                    provider=order_request.provider
                ).update(status=OrderRequestStatus.TERMINATE)

                order_request.status = OrderRequestStatus.ACCEPTED
                order_request.save(update_fields=["status"])
        except Exception as e:
            raise Exception("Order Request not Acceptable.")