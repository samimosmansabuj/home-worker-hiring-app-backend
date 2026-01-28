from django.shortcuts import render, get_object_or_404
from .serializers import ServiceCategorySerializer, OrderSerializer, OrderRequestSerializer, OrderRequestSerializerForOrder, ReviewAndRatingSerializer, PaymentTransactionSerializer
from find_worker_config.utils import UpdateModelViewSet, PaymentTransactionModule, UpdateReadOnlyModelViewSet, LogActivityModule
from .models import ServiceCategory, Order, OrderRequest, ReviewAndRating, PaymentTransaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from find_worker_config.permissions import ForProviderProfile, IsAdminWritePermissionOnly, HasCustomerProfileSafeModeTypeHeader, ForCustomerProfile, ForAdminProfile
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault, OrderRequestStatus, OrderPaymentStatus, PaymentTransactionType, PaymentAction
from django.db.models import Q
from rest_framework import views
from .services import OrderService
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from account.utils import generate_otp
from account.models import ServiceProviderProfile
from django.db.models import Q

class ServiceCategoryViewSet(UpdateModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAdminWritePermissionOnly]

    def perform_update(self, serializer):
        push_notify_role(
            role=UserRole.CUSTOMER,
            data={
                "type": "CATEGORY_UPDATE",
                "message": "Category Updated!"
            }
        )
        return super().perform_update(serializer)

class OrderRequestViewSets(UpdateModelViewSet):
    queryset = OrderRequest.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = OrderRequestSerializer

class ReviewAndRatingViewSets(UpdateModelViewSet):
    queryset = ReviewAndRating.objects.all()
    serializer_class = ReviewAndRatingSerializer
    permission_classes = [HasCustomerProfileSafeModeTypeHeader]

    def get_queryset(self):
        profile_type = self.request.headers.get("profile-type", "").upper()
        action = self.request.query_params.get("action")
        provider_profile_id = self.request.query_params.get("provider_profile_id")

        if action == "view" and profile_type == UserDefault.CUSTOMER:
            if not provider_profile_id:
                raise Exception("Profile id is missing.")
            provider = get_object_or_404(ServiceProviderProfile, pk=int(provider_profile_id))
            return ReviewAndRating.objects.filter(provider=provider)
        else:
            if profile_type == UserRole.ADMIN:
                if not provider_profile_id:
                    raise Exception("Profile id is missing.")
                # provider = get_object_or_404(ServiceProviderProfile, pk=int(provider_profile_id))
                return ReviewAndRating.objects.filter(provider__id=int(provider_profile_id))
            elif profile_type == UserDefault.CUSTOMER:
                return ReviewAndRating.objects.filter(customer=self.request.user.hasCustomerProfile)
            elif profile_type == UserDefault.PROVIDER:
                return ReviewAndRating.objects.filter(provider=self.request.user.hasServiceProviderProfile)

    def get_user(self):
        profile_type = self.request.headers.get("profile-type", "")
        return self.request.user


# Order Section For Customer----------------------------------------------------------
class CustomerOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [ForCustomerProfile]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user.hasCustomerProfile
        ).prefetch_related("order_requests")

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

    def perform_create(self, serializer):
        instance = serializer.save()
        self.create_log("Create New Order", instance, for_notify=True)
        return instance
    
    def perform_update(self, serializer):
        instance = serializer.save()
        self.create_log("Update Order", instance, for_notify=False)
        return instance

    @action(detail=True, methods=["get"], url_path=r"requests(?:/(?P<request_id>\d+))?")
    def requests(self, request, *args, **kwargs):
        order = self.get_object()
        request_id = kwargs.get("request_id")
        if request_id:
            order_request = get_object_or_404(
                order.order_requests,
                id=request_id
            )
            serializer = OrderRequestSerializerForOrder(order_request)
            return Response(
                {"status": True, "data": serializer.data},
                status=status.HTTP_200_OK
            )
        serializer = OrderRequestSerializerForOrder(
            order.order_requests.all(),
            many=True
        )
        return Response(
            {"status": True, "data": serializer.data},
            status=status.HTTP_200_OK
        )
    
    def order_action_permission(self, order, order_request, action_status):
        if action_status not in (OrderRequestStatus.ACCEPTED, OrderRequestStatus.PENDING, OrderRequestStatus.REJECTED):
            raise Exception("Wrong Status Value.")
        if OrderRequest.objects.filter(order=order, status=OrderRequestStatus.ACCEPTED).exists():
            raise Exception("Already one of request accepted!")
        if order.customer.user == order_request.provider.user:
            raise Exception("Same user can't accept the order request")
        return True

    @action(detail=True, methods=["post"], url_path="accept-request/(?P<request_id>\\d+)")
    def accept_request(self, request, *args, **kwargs):
        action_status = request.data.get("action_status", "").upper()
        order = self.get_object()
        order_request = OrderRequest.objects.get(
            id=self.kwargs.get("request_id"),
            order=order
        )
        
        if action_status == "CANCEL":
            if order_request.status in [OrderRequestStatus.ACCEPTED] and order.status in [OrderStatus.ACCEPT]:
                with transaction.atomic():
                    OrderRequest.objects.filter(
                        order=order
                    ).update(status=OrderRequestStatus.PENDING)
                    order.provider = None
                    order.status=OrderStatus.ACTIVE
                    order.amount=0
                    order.save(update_fields=["status", "amount", "provider"])
                    self.create_log(
                        "Request Cancel", entity=order, for_notify=True, user=order_request.provider.user,
                        metadata={"reference_user_id": self.request.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                    )
                    return Response(
                        {
                            "status": True,
                            "message": "Accepted Request Cancel."
                        }
                    )
            else:
                raise Exception("You can't Cancel This Request.")
        self.order_action_permission(order, order_request, action_status)
        
        if action_status == OrderRequestStatus.REJECTED:
            with transaction.atomic():
                if order_request.status == OrderRequestStatus.REJECTED:
                    raise Exception("This order request already rejected.")
                order_request.status = OrderRequestStatus.REJECTED
                order_request.save(update_fields=["status"])
                self.create_log(
                    "Request Rejected", entity=order, for_notify=True, user=order_request.provider.user,
                    metadata={"reference_user_id": self.request.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                )
                return Response({"status": True, "message": "Order Request Rejected"}, status=status.HTTP_200_OK)
        elif action_status == OrderRequestStatus.ACCEPTED:
            with transaction.atomic():
                amount = request.data.get("amount", None)
                if not amount:
                    raise Exception("Final Amount Must be Set.")
                OrderService.accept_order(order, order_request, float(amount))
                self.create_log(
                    "Request Accept", entity=order, for_notify=True, user=order_request.provider.user,
                    metadata={"reference_user_id": self.request.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                )
                return Response({"status": True, "message": "Order Request Accepted"}, status=status.HTTP_200_OK)
    
    def get_accepted_order_request(self, order, request_id=None):
        if request_id:
            try:
                return get_object_or_404(
                    order.order_requests,
                    id=request_id,
                    status=OrderRequestStatus.ACCEPTED
                )
            except:
                return get_object_or_404(OrderRequest, order=order, status=OrderRequestStatus.ACCEPTED)
        else:
            return get_object_or_404(
                order.order_requests,
                status=OrderRequestStatus.ACCEPTED
            )

    @action(detail=True, methods=["get"], url_path=r"payment(?:/(?P<request_id>\d+))?")
    def order_payment(self, request, *args, **kwargs):
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
                order_request = self.get_accepted_order_request(order, kwargs.get("request_id", None))

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
                    metadata={"reference_user_id": order.provider.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                )
                self.create_log(
                    "Order Confirm", entity=order, for_notify=True, user=order.provider.user,
                    metadata={"reference_user_id": order.customer.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                )
                return Response(
                    {"status": True, "message": "Order payment complete!"},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {"status": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get", "post"], url_path=r"review")
    def order_review(self, request, *args, **kwargs):
        order = self.get_object()
        order_request = self.get_accepted_order_request(order=order)
        user = request.user
        if request.method == "GET":
            review = ReviewAndRating.objects.get(order=order, customer=user.hasCustomerProfile)
            serializer = ReviewAndRatingSerializer(review, context={"request": request, "present": "in_order"})
            return Response(
                {"status": True, "data": serializer.data},
                status=status.HTTP_200_OK
            ) 
        if request.method == "POST":
            if order.status not in (OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE):
                raise Exception("Only Complete Work can review.")
            elif ReviewAndRating.objects.filter(order=order).exists():
                raise Exception("Review already submited.")
            try:
                with transaction.atomic():
                    serializer = ReviewAndRatingSerializer(data=request.data, context={"request": request, "order": order, "present": "in_order"})
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    self.create_log(
                        "Submit Feedback", entity=order, for_notify=True, user=order.provider.user,
                        metadata={"reference_user_id": order.customer.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                    )
                    return Response(
                        {"status": True, "message": "Thanks for your reviews.", "data": serializer.data},
                        status=status.HTTP_200_OK
                    )
            except ValidationError:
                error = {key: str(value[0]) for key, value in serializer.errors.items()}
                return Response(
                    {"status": False, "message": error},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                return Response(
                    {"status": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

    def destroy(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            if order.status != OrderStatus.ACTIVE:
                raise PermissionDenied("Order cannot be deleted at this stage.")
            self.create_log("Delete Order")
            return super().destroy(request, *args, **kwargs)
            return Response(
                {
                    'status': True,
                    'message': self.delete_message,
                }, status=status.HTTP_200_OK
            )
        except PermissionDenied as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_406_NOT_ACCEPTABLE
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 


# Order Section For Provider----------------------------------------------------------
class ProviderOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, ForProviderProfile]

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

    def get_queryset(self):
        provider = self.request.user.hasServiceProviderProfile
        action = self.request.query_params.get("action")
        qs = Order.objects.select_related(
            "category", "customer", "provider"
        ).prefetch_related(
            "order_requests"
        )
        if action == "active":
            return qs.filter(
                status__in=[OrderStatus.ACTIVE]
            )
        elif action == "requested":
            return qs.filter(
                order_requests__provider=provider,
                order_requests__status=OrderRequestStatus.PENDING,
                status=OrderStatus.ACTIVE
            ).distinct()
        elif action == "accept":
            return qs.filter(
                provider=provider,
                status__in=[OrderStatus.ACCEPT, OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE, OrderStatus.REFUND]
            )
        elif action == "terminated":
            return qs.filter(
                order_requests__provider=provider,
                order_requests__status=OrderRequestStatus.TERMINATE
            ).distinct()
        else:
            return qs.filter(
                Q(provider=provider) |
                Q(order_requests__provider=provider)
            ).distinct()

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            return Response(
                {
                    'status': True,
                    'count': len(response.data),
                    'data': response.data
                }, status=status.HTTP_200_OK
            )
        except PermissionDenied as e:
            return Response(
                {
                    'status': False,
                    'messgae': str(e),
                }, status=status.HTTP_406_NOT_ACCEPTABLE
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'messgae': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                'status': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK
        )

    def check_provider_in_request(self, provider: object, order_requests: queryset):
        for order_request in order_requests:
            if order_request.provider_id == provider.id:
                return order_request
        return None

    @action(detail=True, methods=["post", "get"], url_path="send-request")
    def send_request(self, request, *args, **kwargs):
        if request.method == "POST":
            try:
                with transaction.atomic():
                    order = self.get_object()
                    serializer = OrderRequestSerializer(
                        data=request.data,
                        context={"request": request, "order": order}
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save(
                        order=order,
                        provider=request.user.hasServiceProviderProfile
                    )
                    self.create_log("Send Request For Order", serializer.instance)
                    return Response(
                        {"status": True, "data": serializer.data},
                        status=status.HTTP_201_CREATED
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
        elif request.method == "GET":
            order_requests = self.get_object().order_requests.all()
            order_request = self.check_provider_in_request(request.user.hasServiceProviderProfile, order_requests)
            if order_request:
                get_response = OrderRequestSerializerForOrder(order_request).data
            else:
                get_response = "You have no request for this order!"
            return Response(
                {
                    "status": True,
                    "data": get_response
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["patch", "delete"], url_path="update-request")
    def update_request(self, request, *args, **kwargs):
        if request.method == "PATCH":
            try:
                order = self.get_object()
                order_request = OrderRequest.objects.get(
                    order=order,
                    provider=request.user.hasServiceProviderProfile
                )
                if not order_request:
                    raise Exception("You have not sent any request for this order.")
                if order_request.status == OrderRequestStatus.ACCEPTED:
                    raise Exception("Order Request Already Accepted.")
                if order.status != OrderStatus.ACTIVE:
                    raise Exception(f"Can't Update Your Request Right Now.")
                with transaction.atomic():
                    update_fields = []
                    if request.data.get("budget"):
                        order_request.budget = request.data.get("budget")
                        update_fields.append("budget")
                    if request.data.get("message"):
                        order_request.message = request.data.get("message")
                        update_fields.append("message")
                    if update_fields:
                        order_request.save(update_fields=update_fields)
                    request_serializer = OrderRequestSerializer(order_request)
                    return Response(
                        {
                            "status": True,
                            "message": "Request Update Succefully!",
                            "data": request_serializer.data
                        }, status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {
                        "status": False,
                        "message": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        if request.method == "DELETE":
            try:
                order = self.get_object()
                if order.status not in [OrderStatus.ACTIVE, OrderStatus.ACCEPT]:
                    return Response(
                        {"status": False, "message": "Can't Cancel Request."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                order_request = OrderRequest.objects.get(
                    order=order,
                    provider=request.user.hasServiceProviderProfile
                )
                # order_request.delete()
                order_request.status = OrderRequestStatus.REJECTED
                order_request.save(update_fields=["status"])
                return Response(
                    {
                        "status": True,
                        "message": "Request Cancel Succefully!"
                    }, status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        "status": False,
                        "message": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST
                )

    def start_work_progress(self, request, order: object):
        # Error Handling, Permission and Acceptance For Start Work Progress
        if order.payment_transactions.filter(type=PaymentTransactionType.HOLD, action=PaymentAction.PAYMENT_HOLD).exists():
            raise Exception("Duplicate payment hold detected.")
        if order.status == OrderStatus.IN_PROGRESS:
            raise Exception("The order is already in progress!")
        if order.status != OrderStatus.CONFIRM:
            raise Exception("Only confirm order can start work progress!")
        
        with transaction.atomic():
            # Payment Transaction----
            payment = PaymentTransactionModule(
                user=request.user,
                amount=order.amount,
                reference_object=order,
                type=PaymentTransactionType.HOLD,
                action=PaymentAction.PAYMENT_HOLD
            )
            payment.payment_transaction()
            
            # Order update After payment transanction-------
            order.status = OrderStatus.IN_PROGRESS
            order.confirmation_OTP = generate_otp(length=6)
            order.save(update_fields=["status", "confirmation_OTP"])
            message = "Work in Progress Start."
            return message
    
    def mark_work_complete(self, request, order):
        # Error Handling, Permission and Acceptance For Mark Complete
        if order.status == OrderStatus.COMPLETED:
            raise Exception("The order is already completed!")
        if order.status != OrderStatus.IN_PROGRESS:
            raise Exception("Only in progress order can complete the order!")
        otp_code = request.data.get("otp_code", None)
        if not otp_code:
            raise Exception("Need to submit otp for Complete the Order.")
        if otp_code != order.confirmation_OTP:
            raise Exception("OTP doesn't match.")
        with transaction.atomic():
            order.status = OrderStatus.COMPLETED
            order.save(update_fields=["status"])
            message = "Work Completed"
            return message

    @action(detail=True, methods=["patch"], url_path="status-action")
    def status_action(self, request, *args, **kwargs):
        if request.method == "PATCH":
            try:
                with transaction.atomic():
                    order = self.get_object()
                    message = ""
                    order_request = OrderRequest.objects.get(
                        order=order,
                        provider=request.user.hasServiceProviderProfile
                    )
                    action_status = request.data.get("action_status", "").upper()
                    if action_status not in ["IN_PROGRESS", "COMPLETED", "PARTIAL_COMPLETE"]:
                        raise Exception("Wrong Action Status.")
                    
                    if action_status == OrderStatus.IN_PROGRESS:
                        message = self.start_work_progress(request, order)
                        self.create_log(
                            "Order Work Start", entity=order, for_notify=True, user=order.customer.user,
                            metadata={"reference_user_id": order.provider.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                        )
                    if action_status == OrderStatus.COMPLETED:
                        message = self.mark_work_complete(request, order)
                        self.create_log(
                            "Order Complete", entity=order, for_notify=True, user=order.customer.user,
                            metadata={"reference_user_id": order.provider.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                        )

                    return Response(
                        {"status": True, "message": message},
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {
                        "status": False,
                        "message": str(e)
                    }, status=status.HTTP_400_BAD_REQUEST
                )


# Order Section For Admin----------------------------------------------------------
class AdminOrderViewSet(UpdateModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
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

    def payable_amount(self, amount):
        charge = (amount * 10) / 100
        return amount - charge
    
    def get_accepted_order_request(self, order):
        return get_object_or_404(
            order.order_requests,
            status=OrderRequestStatus.ACCEPTED
        )

    def error_and_permission_handle(self, order, payable_amount):
        if payable_amount is None:
            raise Exception("'payable_amount' must be set.")
        if order.payment_transactions.filter(type=PaymentTransactionType.DEBIT, action=PaymentAction.SEND_PROVIDER).exists():
            raise Exception("Duplicate payment disbursement detected.")
        if order.status not in (OrderStatus.COMPLETED, OrderStatus.PARTIAL_COMPLETE):
            raise Exception("Only Complete Order can disbursement")
        elif order.payment_status != OrderPaymentStatus.PAID:
            raise Exception("Only Paid order can disbursement")
        elif order.payment_status == OrderPaymentStatus.DISBURSEMENT:
            raise Exception("Already payment disbursement to worker.")
        if float(payable_amount) != float(self.payable_amount(order.amount)):
            raise Exception("Payable Amount mismatch!")
        return True

    @action(detail=True, methods=["post", "get"], url_path="pay-to-worker")
    def pay_to_worker(self, request, *args, **kwargs):
        order = self.get_object()
        if request.method == "GET":
            try:
                return Response(
                    {
                        "status": True,
                        "data": {
                            "payable_amount": float(order.amount - (order.amount * 10 / 100))
                        }
                    }, status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response({"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == "POST":
            try:
                order_request = self.get_accepted_order_request(order)
                if not order_request:
                    raise Exception("Accept order request not found for this order.")
                
                payable_amount = request.data.get("payable_amount", None)
                self.error_and_permission_handle(order, payable_amount)

                with transaction.atomic():
                    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                    # Here Code for Payment Process and Build Logic
                    # payment_information = payment information value json
                    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

                    # Payment Transaction----
                    payment = PaymentTransactionModule(
                        user=order.provider.user,
                        amount=order.amount,
                        reference_object=order,
                        type=PaymentTransactionType.DEBIT,
                        action=PaymentAction.SEND_PROVIDER
                    )
                    payment.payment_transaction()
                    
                    # Order update After payment transanction-------
                    order.payment_status = OrderPaymentStatus.DISBURSEMENT
                    order.save(update_fields=["payment_status"])
                    self.create_log(
                        "Your Payment Complete", entity=order, for_notify=True, user=order.provider.user,
                        metadata={"reference_user_id": order.customer.user.id, "reference_object_id": order_request.id, "reference_object_type": "OrderRequest"}
                    )
                    return Response(
                        {"status": True, "message": "Pay to Worker Successfully Complete!"},
                        status=status.HTTP_200_OK
                    )
            except Exception as e:
                return Response(
                    {"status": False, "message": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )



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

# =================== Payment transaction Section Start===================================
# ==========================================================================================


    
