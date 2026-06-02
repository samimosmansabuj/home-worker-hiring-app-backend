from rest_framework.views import APIView
from task.models import PaymentTransaction, Order, OrderRefundRequest, OrderChangesRequest, OrderAttachment
from .models import AdminWallet
from rest_framework_simplejwt.views import TokenObtainPairView
from find_worker_config.permissions import IsAdmin
from account.models import CustomerProfile, ServiceProviderProfile, User, OTP
from .admin_serializers import AdminCreateSerializer, AdminLoginSerializer, AdminCustomerSerializer, AdminProviderSerializer, PaymentTransactionSerializer, OrderRefundRequestSerializer, OrderRefundRequestActionSerializer, AdminOrderPaymentTransactionSerializer, AdminOrderSerializer, AdminOrderChangesRequestSerializer, AdminOrderAttachmentSerializer
from find_worker_config.utils import UpdateModelViewSet, UpdateReadOnlyModelViewSet, PaymentTransactionModule
from rest_framework.response import Response
from django.db import transaction
from rest_framework import status
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from find_worker_config.model_choice import OrderStatus, UserRole, UserDefault, PaymentTransactionType, RefundStatus, OrderPaymentStatus, PaymentAction
from django.db.models import Q
import requests
from .filters import PaymentTransactionFilter, OrderRefundFilter, OrderFilter
from django.utils import timezone

class DashboardAPIView(APIView):
    def get_order_for_pay(self):
        orders = Order.objects.filter(
            status=OrderStatus.COMPLETED,
            payment_status=OrderPaymentStatus.PAID
        )
        serializer = AdminOrderSerializer(orders, many=True)
        return serializer.data
    
    def get(self, request, *args, **kwargs):
        active_order = Order.objects.filter(
            status__in=[OrderStatus.ACCEPT, OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS]
        ).count()
        complete_order = Order.objects.filter(
            status__in=[OrderStatus.COMPLETED]
        ).count()
        total_user = User.objects.filter(
            role=UserRole.USER
        ).count()
        
        admin_wallet, _ = AdminWallet.objects.get_or_create()
        total_revenue = admin_wallet.current_balance
        return Response(
            {
                "status": True,
                "data": {
                    "active_order": active_order,
                    "complete_order": complete_order,
                    "total_user": total_user,
                    "total_revenue": total_revenue,
                    "order_for_pay": self.get_order_for_pay()
                }
            }, status=status.HTTP_200_OK
        )


class AdminAuthViews(TokenObtainPairView):
    serializer_class = AdminLoginSerializer
    
    def post(self, request: Request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(
                {
                    "status": True,
                    "data": serializer.validated_data
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class AdminUserViews(UpdateModelViewSet):
    queryset = User.objects.all()
    serializer_class = AdminCreateSerializer
    permission_classes = [IsAdmin]

class AdminProviderViews(UpdateReadOnlyModelViewSet):
    queryset = ServiceProviderProfile.objects.all()
    serializer_class = AdminProviderSerializer
    permission_classes = [IsAdmin]

class AdminCustomerViews(UpdateReadOnlyModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAdmin]

class AdminOrderViewSet(UpdateReadOnlyModelViewSet):
    queryset = Order.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAdmin]
    filterset_class = OrderFilter

    @action(detail=True, methods=["post"], url_path="pay-provider")
    def pay_provider(self, request, pk=None):
        try:
            order = self.get_object()
            if order.status != OrderStatus.COMPLETED:
                raise Exception("Order not completed")
            if order.payment_status != OrderPaymentStatus.PAID:
                raise Exception("Payment not received")

            data = request.data
            transaction_id = data.get("transaction_id")
            PaymentTransactionModule(
                user=order.provider.user,
                profile=UserDefault.PROVIDER,
                amount=order.amount,
                reference_object=order,
                type=PaymentTransactionType.DEBIT,
                action=PaymentAction.SEND_PROVIDER,
                transaction_id=transaction_id
            ).payment_transaction()

            order.payment_status = OrderPaymentStatus.DISBURSEMENT
            order.save(update_fields=["payment_status"])

            return Response({
                "status": True,
                "message": "Payment sent to provider"
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": True,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"], url_path="transactions")
    def transactions(self, request, pk=None):
        order = self.get_object()
        transactions = PaymentTransaction.objects.filter(
            order=order
        ).select_related("user").order_by("-created_at")
        serializer = AdminOrderPaymentTransactionSerializer(
            transactions,
            many=True,
            context={"request": request}
        )
        return Response(
            {
                "status": True,
                "results": serializer.data
            }, status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["get"], url_path="change-requests")
    def change_requests(self, request, pk=None):
        order = self.get_object()
        changes = OrderChangesRequest.objects.filter(
            order=order
        ).order_by("-created_at")
        serializer = AdminOrderChangesRequestSerializer(
            changes,
            many=True,
            context={"request": request}
        )
        return Response(
            {
                "status": True,
                "results": serializer.data
            }, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["get"], url_path="attachments")
    def attachments(self, request, pk=None):
        order = self.get_object()
        attachments = OrderAttachment.objects.filter(
            order=order
        ).order_by("-created_at")
        serializer = AdminOrderAttachmentSerializer(
            attachments,
            many=True,
            context={"request": request}
        )
        return Response(
            {
                "status": True,
                "results": serializer.data
            }, status=status.HTTP_200_OK
        )

class PaymentTransactionViewSets(UpdateReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAdmin]
    filterset_class = PaymentTransactionFilter

class OrderRefundViewSets(UpdateReadOnlyModelViewSet):
    queryset = OrderRefundRequest.objects.all()
    serializer_class = OrderRefundRequestSerializer
    permission_classes = [IsAdmin]
    filterset_class = OrderRefundFilter

    @action(detail=True, methods=["post"], url_path="action")
    def method_admin_action(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                refund_object = self.get_object()
                serializer = OrderRefundRequestActionSerializer(data=request.data, context={"request": request, "refund_object": refund_object})
                serializer.is_valid(raise_exception=True)
                refund_status = serializer.validated_data["status"]
                admin_note = serializer.validated_data.get("admin_note")
                
                if refund_status in [RefundStatus.APPROVED, RefundStatus.REJECTED]:
                    # Refund Object Update----
                    refund_object.status = refund_status
                    refund_object.processed_by = request.user
                    refund_object.processed_at = timezone.now()
                    # self.create_log(
                    #     f"Refund {refund_status}", entity=refund_object, for_notify=True, user=refund_object.customer.user,
                    #     metadata={"reference_object_id": refund_object.order.id, "reference_object_type": "Order"}
                    # )
                elif refund_status == RefundStatus.COMPLETED and refund_object.status == RefundStatus.APPROVED:
                    trnx_id = serializer.validated_data.get("trnx_id" or None)
                    # amount = serializer.validated_data.get("amount" or None)
                    # if amount and refund_object.refund_amount != amount:
                    #     raise Exception("Order Amount not same!")
                    if not trnx_id:
                        raise Exception("Transaction ID must be submited.")
                    # Refund Object Update----
                    refund_object.status = refund_status
                    refund_object.processed_by = request.user
                    refund_object.processed_at = timezone.now()
                    order = refund_object.order
                    # Order Object Update----
                    order.status = OrderStatus.REFUND
                    order.payment_status = OrderPaymentStatus.REFUND
                    order.save()
                    # Payment Transaction----
                    payment = PaymentTransactionModule(
                        user=refund_object.customer.user,
                        profile=UserDefault.CUSTOMER,
                        amount=refund_object.refund_amount,
                        reference_object=refund_object,
                        type=PaymentTransactionType.DEBIT,
                        action=PaymentAction.REFUND_CUSTOMER,
                        transaction_id=trnx_id
                    )
                    payment.payment_transaction()
                    # self.create_log(
                    #     f"Refund {refund_status}", entity=refund_object, for_notify=True, user=refund_object.customer.user,
                    #     metadata={"reference_object_id": refund_object.order.id, "reference_object_type": "Order"}
                    # )
                else:
                    raise Exception(f"Your order is {refund_object.status} and can't update right now!")
                
                if admin_note:
                    refund_object.admin_note = admin_note
                refund_object.save()
                return Response(
                    {
                        "status": True,
                        "message": f"Refund Status Update at {refund_status}"
                    }, status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )


