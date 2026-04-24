from django.shortcuts import render, get_object_or_404
from .serializers import ServiceCategorySerializer, ServiceSubCategorySerializer, OrderSerializer, ReviewAndRatingSerializer, PaymentTransactionSerializer, OrderRefundRequestSerializer
from find_worker_config.utils import UpdateModelViewSet, PaymentTransactionModule, UpdateReadOnlyModelViewSet, LogActivityModule
from .models import ServiceCategory, ServiceSubCategory, Order, ReviewAndRating, PaymentTransaction, OrderRefundRequest
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from find_worker_config.permissions import ForProviderProfile, IsAdminWritePermissionOnly, HasCustomerProfileSafeModeTypeHeader, ForCustomerProfile, ForAdminProfile
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, OrderPaymentStatus, PaymentTransactionType, PaymentAction, RefundStatus
from django.db.models import Q
from rest_framework import views
from .services import OrderService
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from account.utils import generate_otp
from account.models import ServiceProviderProfile
from django.db.models import Q
from django.utils import timezone
from rest_framework.generics import CreateAPIView

# ============================================================
# Category Views Section ===================
class ServiceCategoryViewSet(UpdateModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAdminWritePermissionOnly]

    def perform_update(self, serializer):
        push_notify_role(
            role=UserRole.ADMIN,
            data={
                "type": "CATEGORY_UPDATE",
                "message": "Category Updated!"
            }
        )
        return super().perform_update(serializer)

class ServiceSubCategoryViewSet(UpdateModelViewSet):
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer
    permission_classes = [IsAdminWritePermissionOnly]

    def perform_update(self, serializer):
        push_notify_role(
            role=UserRole.ADMIN,
            data={
                "type": "CATEGORY_UPDATE",
                "message": "Sub Category Updated!"
            }
        )
        return super().perform_update(serializer)

# Category Views Section ===================
# ============================================================


# ============================================================
# ========Custom Offer Order Create===================
class CustomerOrderCreateViews(CreateAPIView):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    'status': True,
                    'message': 'Custom offer created!',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

# ========Custom Offer Order Create===================
# ============================================================


class ProviderOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [ForProviderProfile]

    def get_queryset(self):
        provider = self.request.user.hasServiceProviderProfile
        return Order.objects.filter(provider=provider)
    
    @action(detail=True, methods=["post"], url_path="start-work")
    def start_work(self, request, pk=None):
        order = self.get_object()

        if order.status != OrderStatus.CONFIRM:
            raise ValueError("Order must be confirmed")

        order.status = OrderStatus.IN_PROGRESS
        order.confirmation_OTP = generate_otp(6)
        order.save(update_fields=["status", "confirmation_OTP"])

        return Response({
            "status": True,
            "message": "Work started"
        })


    @action(detail=True, methods=["post"], url_path="complete-work")
    def complete_work(self, request, pk=None):
        order = self.get_object()
        otp = request.data.get("otp")

        if order.status != OrderStatus.IN_PROGRESS:
            raise ValidationError("Order not in progress")

        if otp != order.confirmation_OTP:
            raise ValidationError("Invalid OTP")

        order.status = OrderStatus.COMPLETED
        order.save(update_fields=["status"])

        return Response({
            "status": True,
            "message": "Work completed"
        })

class ReviewAndRatingViewSets(UpdateModelViewSet):
    queryset = ReviewAndRating.objects.all()
    serializer_class = ReviewAndRatingSerializer
    permission_classes = [ForCustomerProfile]



class AdminOrderViewSet(UpdateModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [ForAdminProfile]

    @action(detail=True, methods=["post"], url_path="pay-provider")
    def pay_provider(self, request, pk=None):
        order = self.get_object()

        if order.status != OrderStatus.COMPLETED:
            raise ValidationError("Order not completed")

        if order.payment_status != OrderPaymentStatus.PAID:
            raise ValidationError("Payment not received")

        PaymentTransactionModule(
            user=order.provider.user,
            amount=order.amount,
            reference_object=order,
            type=PaymentTransactionType.DEBIT,
            action=PaymentAction.SEND_PROVIDER
        ).payment_transaction()

        order.payment_status = OrderPaymentStatus.DISBURSEMENT
        order.save(update_fields=["payment_status"])

        return Response({
            "status": True,
            "message": "Payment sent to provider"
        })


# ==========================================================================================
# =================== Payment transaction Section Start===================================
class PaymentTransactionViewSets(UpdateReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == UserRole.USER:
            pt = PaymentTransaction.objects.filter(
                user=self.request.user
            ).filter(
                Q(type=PaymentTransactionType.CREDIT) | Q(type=PaymentTransactionType.DEBIT)
            )
        elif self.request.user.role == UserRole.ADMIN:
            pt = PaymentTransaction.objects.all()
        else:
            raise Exception("Payment transaction not get for the user.")
        return pt

class OrderRefundViewSets(UpdateReadOnlyModelViewSet):
    queryset = OrderRefundRequest.objects.all()
    serializer_class = OrderRefundRequestSerializer
    permission_classes = [ForAdminProfile]

    def create_log(self, action, entity=None, for_notify=False, user=None, metadata={}):
        data = {
            "user": user or self.request.user,
            "action": action,
            "entity": entity,
            "request": self.request,
            "for_notify": for_notify,
            "metadata": metadata,
        }
        log = LogActivityModule(data)
        log.create()

    @action(detail=True, methods=["post"], url_path="action")
    def method_admin_action(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                refund_object = self.get_object()

                serializer = OrderRefundRequestActionSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                refund_status = serializer.validated_data["status"]
                admin_note = serializer.validated_data["admin_note"]
                
                if refund_object.status == refund_status:
                    raise Exception(f"Order is already at {refund_object.status}")
                if refund_status in [RefundStatus.APPROVED, RefundStatus.REJECTED]:
                    # Refund Object Update----
                    refund_object.status = refund_status
                    refund_object.processed_by = request.user
                    refund_object.processed_at = timezone.now()
                    self.create_log(
                        f"Refund {refund_status}", entity=refund_object, for_notify=True, user=refund_object.customer.user,
                        metadata={"reference_object_id": refund_object.order.id, "reference_object_type": "Order"}
                    )
                elif refund_status == RefundStatus.COMPLETED and refund_object.status == RefundStatus.APPROVED:
                    trnx_id = serializer.validated_data.get("trnx_id" or None)
                    amount = serializer.validated_data.get("amount" or None)
                    if amount and refund_object.refund_amount != amount:
                        raise Exception("Order Amount not same!")
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
                        amount=refund_object.refund_amount,
                        reference_object=refund_object,
                        type=PaymentTransactionType.DEBIT,
                        action=PaymentAction.REFUND_CUSTOMER
                    )
                    payment.payment_transaction()
                    self.create_log(
                        f"Refund {refund_status}", entity=refund_object, for_notify=True, user=refund_object.customer.user,
                        metadata={"reference_object_id": refund_object.order.id, "reference_object_type": "Order"}
                    )
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

# =================== Payment transaction Section Start===================================
# ==========================================================================================


    
