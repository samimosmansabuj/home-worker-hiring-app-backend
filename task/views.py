from django.shortcuts import get_object_or_404
from .serializers import ServiceCategorySerializer, ServiceSubCategorySerializer, ReviewAndRatingSerializer, PaymentTransactionSerializer, CompleteSerializer, CounterSerializer, ProposeNewTimeActionSerializer, ProposeNewTimeSerializer, SetHourSerializer, OrderSerializerAll, StartWorkSerializer, ReviewAndRatingSerializer, OrderRefundRequestSerializer
from find_worker_config.utils import UpdateModelViewSet, PaymentTransactionModule, UpdateReadOnlyModelViewSet, LogActivityModule
from .models import ServiceCategory, ServiceSubCategory, Order, ReviewAndRating, PaymentTransaction, OrderRefundRequest
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from find_worker_config.permissions import IsAdminWritePermissionOnly, ForCustomerProfile, ForAdminProfile
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, OrderPaymentStatus, PaymentTransactionType, PaymentAction, RefundStatus, UserDefault
from django.db.models import Q
from django.db import transaction
from account.utils import generate_otp
from django.db.models import Q
from django.utils import timezone
from rest_framework.generics import CreateAPIView
from math import radians, cos, sin, asin, sqrt

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
# ========Order Views Section===================

# -----------Custom Offer Order Start-------------
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

# -----------Custom Offer Order End-------------


class CustomerOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

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

    def get_serializer_context(self):
        return {"request": self.request, "profile_type": UserDefault.CUSTOMER}

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(customer=user.customer_profile)
    
    @action(detail=True, methods=["post"])
    def counter(self, request, *args, **kwargs):
        try:
            serializer = CounterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            order = self.get_object()
            serializer.save(
                order=order, profile_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    "status": True,
                    "message": "Counter Offer Sent"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"])
    def accept(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order already {order.status}.")
        # elif order.status == OrderStatus.ACCEPT:
        #     raise ValueError("Order already accept.")
        with transaction.atomic():
            order.status = OrderStatus.ACCEPT
            order.accepted_at = timezone.localtime(timezone.now())
            order.save()
            return Response(
                {
                    "status": True,
                    "message": "Order accept and awaiting for payment."
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["get"], url_path="pay-and-confirm")
    def pay_and_confirm(self, request, *args, **kwargs):
        try:
            order = self.get_object()

            # Error Handling, Permission and Acceptance For Payment
            if order.payment_transactions.filter(type=PaymentTransactionType.CREDIT, action=PaymentAction.ORDER_PAYMENT).exists():
                return Response(
                    {"status": False, "message": "Duplicate payment detected."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if order.status == OrderStatus.CONFIRM and order.payment_status == OrderPaymentStatus.PAID:
                raise Exception("The order is already confirm!")
            if not (order.status == OrderStatus.ACCEPT and order.payment_status == OrderPaymentStatus.UNPAID):
                return Response(
                    {"status": False, "message": "Only accept and Unpaid order can payment to confirm!"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                # Here Code for Payment Process and Build Logic
                # payment_information = payment information value json
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

                # Payment Transaction----
                payment = PaymentTransactionModule(
                    user=request.user,
                    amount=order.amount,
                    reference_object=order,
                    type=PaymentTransactionType.CREDIT,
                    action=PaymentAction.ORDER_PAYMENT
                )
                payment.payment_transaction()
                
                # Order update After payment transanction-------
                order.status = OrderStatus.CONFIRM
                order.payment_status = OrderPaymentStatus.PAID
                order.save(update_fields=["status", "payment_status"])
                self.create_log(
                    "Order Payment Complete", entity=order, for_notify=True, user=order.customer.user,
                    metadata={"reference_user_id": order.provider.user.id}
                )
                self.create_log(
                    "Order Confirm", entity=order, for_notify=True, user=order.provider.user,
                    metadata={"reference_user_id": order.customer.user.id}
                )
                return Response(
                    {"status": True, "message": "Order pay and confirm!"},
                    status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="propose-new-time")
    def propose_new_time(self, request, *args, **kwargs):
        data = request.data
        action = data.pop("action", None)
        if action == "create":
            serializer = ProposeNewTimeSerializer(data=request.data)
        elif action == "update":
            serializer = ProposeNewTimeActionSerializer(data=request.data)
        else:
            raise Exception("Action not mention!")
        serializer.is_valid(raise_exception=True)
        serializer.save(order=self.get_object(), profile_type=UserDefault.CUSTOMER)
        return Response(
            {
                "status": True,
                "message": serializer.get_response_message()
            }, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        order = self.get_object()
        data = request.data
        with transaction.atomic():
            if order.status in [OrderStatus.PENDING, OrderStatus.ACCEPT] and order.payment_status == OrderPaymentStatus.UNPAID:
                order.status = OrderStatus.CANCELLED
                order.payment_status = OrderPaymentStatus.CANCELLED
                response_message = "Order Cancelled"
            elif order.status in [OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS] and order.payment_status == OrderPaymentStatus.PAID:
                order.status = OrderStatus.REFUND_REQUEST
                order.payment_status = OrderPaymentStatus.REFUND
                OrderRefundRequest.objects.create(
                    order=order,
                    customer=order.customer,
                    reason=data.pop("message", None),
                    refund_amount=order.amount
                )
                response_message = "Order Cancelled & Refund Processing!"
            else:
                return Response(
                    {
                        "status": False,
                        "message": f"Order already {order.payment_status}"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            order.save()
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="give-feedback")
    def give_feedback(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            serializer = ReviewAndRatingSerializer(data=request.data, context={"order": order, "send_by": UserDefault.CUSTOMER, "request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Thanks for your feedback!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Create method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Update method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Delete method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

class ProviderOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

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

    
    def get_serializer_context(self):
        return {"request": self.request, "profile_type": UserDefault.PROVIDER}

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(provider=user.service_provider_profile)
    
    @action(detail=True, methods=["post"])
    def counter(self, request, *args, **kwargs):
        try:
            serializer = CounterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            order = self.get_object()
            serializer.save(
                order=order, profile_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    "status": True,
                    "message": "Counter Offer Sent"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
        
    @action(detail=True, methods=["get"])
    def accept(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order already {order.status}.")
        # elif order.status == OrderStatus.ACCEPT:
        #     raise ValueError("Order already accept.")
        with transaction.atomic():
            order.status = OrderStatus.ACCEPT
            order.accepted_at = timezone.localtime(timezone.now())
            order.save()
            return Response(
                {
                    "status": True,
                    "message": "Order accept and awaiting for payment."
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="set-work-hour")
    def set_work_hour(self, request, *args, **kwargs):
        try:
            serializer = SetHourSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(order=self.get_object())
            return Response(
                {
                    "status": True,
                    "message": f"{serializer.validated_data.get("set_hour")} Hour Set for complete the work!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"], url_path="propose-new-time")
    def propose_new_time(self, request, *args, **kwargs):
        data = request.data
        action = data.pop("action", None)
        if action == "create":
            serializer = ProposeNewTimeSerializer(data=request.data)
        elif action == "update":
            serializer = ProposeNewTimeActionSerializer(data=request.data)
        else:
            raise Exception("Action not mention!")
        serializer.is_valid(raise_exception=True)
        serializer.save(order=self.get_object(), profile_type=UserDefault.PROVIDER)
        return Response(
            {
                "status": True,
                "message": serializer.get_response_message()
            }, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):
        order = self.get_object()
        data = request.data
        with transaction.atomic():
            if order.status in [OrderStatus.PENDING, OrderStatus.ACCEPT] and order.payment_status == OrderPaymentStatus.UNPAID:
                order.status = OrderStatus.CANCELLED
                order.payment_status = OrderPaymentStatus.CANCELLED
                response_message = "Order Cancelled"
            elif order.status in [OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS] and order.payment_status == OrderPaymentStatus.PAID:
                order.status = OrderStatus.REFUND_REQUEST
                order.payment_status = OrderPaymentStatus.REFUND
                OrderRefundRequest.objects.create(
                    order=order,
                    customer=order.customer,
                    reason=data.pop("message", None),
                    refund_amount=order.amount
                )
                response_message = "Order Cancelled & Refund Processing!"
            else:
                return Response(
                    {
                        "status": False,
                        "message": f"Order already {order.payment_status}"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            order.save()
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="start-work")
    def start_work(self, request, *args, **kwargs):
        try:
            if self.get_object().status != OrderStatus.CONFIRM:
                raise ValueError("Order must be confirmed!")
            serializer = StartWorkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.work_start(order=self.get_object())
            return Response(
                {
                    "status": True,
                    "message": "Work Started!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, *args, **kwargs):
        try:
            if self.get_object().status == OrderStatus.COMPLETED:
                raise ValueError("Order already complete")
            elif self.get_object().status != OrderStatus.IN_PROGRESS:
                raise ValueError("Order must be in progress!")
            
            serializer = CompleteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.complete(order=self.get_object())
            return Response(
                {
                    "status": True,
                    "message": "Work Complete!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="give-feedback")
    def give_feedback(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            serializer = ReviewAndRatingSerializer(data=request.data, context={"order": order, "send_by": UserDefault.PROVIDER, "request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Thanks for your feedback!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Post method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Update method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Delete method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

# ========Order Views Section===================
# ============================================================



class ReviewAndRatingViewSets(UpdateModelViewSet):
    queryset = ReviewAndRating.objects.all()
    serializer_class = ReviewAndRatingSerializer
    permission_classes = [ForCustomerProfile]

class AdminOrderViewSet(UpdateModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializerAll
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


    
