from account.models import HelperSlotException, Address, User
from .serializers import ServiceCategorySerializer, ServiceSubCategorySerializer, ReviewAndRatingSerializer, PaymentTransactionSerializer, CompleteSerializer, CounterSerializer, ProposeNewTimeActionSerializer, ProposeNewTimeSerializer, SetHourSerializer, OrderSerializerAll, StartWorkSerializer, ReviewAndRatingSerializer, OrderRefundRequestSerializer
from find_worker_config.utils import UpdateModelViewSet, PaymentTransactionModule, UpdateReadOnlyModelViewSet
from .models import ServiceCategory, ServiceSubCategory, Order, ReviewAndRating, PaymentTransaction, OrderRefundRequest, OrderChangesRequest
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from find_worker_config.permissions import IsAdminWritePermissionOnly, ForCustomerProfile, ForAdminProfile
from find_worker_config.model_choice import UserRole, OrderStatus, OrderPaymentStatus, PaymentTransactionType, PaymentAction, RefundStatus, UserDefault, LogStatus, HelperSlotExceptionType, OrderChangesRequestStatus, ChangesRequestType
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.generics import CreateAPIView
from core.services.log_engine import handle_log_engine
from datetime import datetime, timedelta
from core.paginations import DefaultPagination
from math import radians, cos, sin, asin, sqrt

# ============================================================
# Category Views Section ===================
class ServiceCategoryViewSet(UpdateModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [IsAdminWritePermissionOnly]

    def perform_update(self, serializer):
        instance = serializer.save()
        handle_log_engine(
            request=self.request, action="CREATE CATEGORY", status=LogStatus.SUCCESS, message="Create a New Category.", entity=instance,
            perform_user=self.request.user
        )
        return instance

class ServiceSubCategoryViewSet(UpdateModelViewSet):
    queryset = ServiceSubCategory.objects.all()
    serializer_class = ServiceSubCategorySerializer
    permission_classes = [IsAdminWritePermissionOnly]

    def perform_update(self, serializer):
        instance = serializer.save()
        handle_log_engine(
            request=self.request, action="CREATE SUB-CATEGORY", status=LogStatus.SUCCESS, message="Create a New Sub-Category.", entity=instance,
            perform_user=self.request.user
        )
        return instance

# Category Views Section ===================
# ============================================================


# ============================================================
# ========Order Views Section===================

# -----------Custom Offer Order Start-------------
class CustomerOrderCreateViews(CreateAPIView):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

    def convert_to_24h(self, time_str):
        try:
            return datetime.strptime(time_str, "%I:%M %p").time()
        except ValueError:
            raise ValidationError("Invalid time format. Expected format like '09:00 AM'")
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            instance = serializer.instance

            handle_log_engine(
                request=request, action="CUSTOM OFFER CREATED", status=LogStatus.SUCCESS, message="Custom Offer Created by Customer", entity=instance,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True, 
                role=UserRole.USER
            )
            handle_log_engine(
                request=request, action="CUSTOM OFFER CREATED", status=LogStatus.SUCCESS, message="Create a New Custom Order from Client", entity=instance,
                perform_user=instance.provider.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER
            )
            return Response(
                {
                    'status': True,
                    'message': 'Custom offer created!',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="CUSTOM OFFER CREATED", status=LogStatus.FAILED, message="Failed to Create Custom Offer",
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=False, logify=True
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            handle_log_engine(
                request=request, action="CUSTOM OFFER CREATED", status=LogStatus.FAILED, message=str(e),
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=False, logify=True
            )
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            handle_log_engine(
                request=request, action="CUSTOM OFFER CREATED", status=LogStatus.FAILED, message=str(e),
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=False, logify=True,
            )
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
    pagination_class = DefaultPagination

    def haversine(self, lat2, lng2):
        lng1, lat1, lng2, lat2 = map(
            radians, [self.user_lng, self.user_lat, lng2, lat2]
        )
        dlon = lng2 - lng1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return round(6371 * c, 2)

    def get_filter_data(self, queryset):
        # ---- Query Params ----
        q = self.request.query_params.get("q")
        category_id = self.request.query_params.get("category_id")
        distance_radius = self.request.query_params.get("distance_radius")
        budget = self.request.query_params.get("budget")
        working_date = self.request.query_params.get("working_date")
        created_at = self.request.query_params.get("created_at")
        status = self.request.query_params.get("status")

        # ---- Search Filter ----
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(details__icontains=q)
            )

        # ---- Category Filter ----
        if category_id:
            queryset = queryset.filter(
                category__id=category_id
            )
        
        # ---- Budget ----
        if budget:
            queryset = queryset.filter(
                hourly_rate__lte=float(budget)
            )

        # ---- Rating Filter ----
        if working_date:
            queryset = queryset.filter(
                working_date=working_date
            )
        
        # ---- Availability ----
        if created_at:
            queryset = queryset.filter(
                created_at=created_at
            )
        
        if status:
            queryset = queryset.filter(
                status=status
            )

        # ---- Distance Calculation (ALWAYS attach) ----
        orders = []
        for order in queryset:
            order_lat = orders.lat
            order_lng = orders.lng

            if not order_lat or not order_lng:
                continue
            distance = self.haversine(order_lat, order_lng)
            print("distance: ", distance)
            # distance = self.get_map_distance(office.lat, office.lng)

            # ---- Distance Radius Filter ----
            if distance_radius:
                if distance <= float(distance_radius):
                    orders.append(order)
            else:
                orders.append(order)
        return orders

    def get_serializer_context(self):
        return {"request": self.request, "profile_type": UserDefault.CUSTOMER}

    def get_queryset(self):
        user = self.request.user
        address = Address.objects.filter(user=user, is_default=True).first()
        if not address:
            return User.objects.none()
        self.user_lat = address.lat
        self.user_lng = address.lng

        user = self.request.user
        return Order.objects.filter(customer=user.customer_profile)
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            orders = self.get_filter_data(queryset)
            # sort_by = request.query_params.get("sort_by")
            # helpers = self.get_sorting_queryset(helpers, sort_by)

            page = self.paginate_queryset(orders)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(orders, many=True)
            return Response({
                "status": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'messgae': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["post"])
    def counter(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            serializer = CounterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(
                order=order, profile_type=UserDefault.CUSTOMER
            )

            handle_log_engine(
                request=request, action="COUNTER OFFER SEND", status=LogStatus.SUCCESS, message="Send Counter Offer from Customer.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Received Counter Offer from Customer"
            )
            return Response(
                {
                    "status": True,
                    "message": "Counter Offer Sent"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}

            handle_log_engine(
                request=request, action="COUNTER OFFER SEND", status=LogStatus.FAILED, message="Failed to Send Counter Offer.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    def get_or_create_slot_exception(self, order, exception_type):
        if not (order.provider and order.working_date and order.working_start_time):
            return None
    
        reason=f"{exception_type} via order"
        if HelperSlotException.objects.filter(order=order).exists():
            slot_exception = HelperSlotException.objects.filter(order=order).first()
            slot_exception.type = exception_type
            slot_exception.date = order.working_date
            slot_exception.start_time = order.working_start_time
            slot_exception.end_time = order.end_time
            slot_exception.reason = reason
            slot_exception.save()
        else:
            slot_exception = HelperSlotException.objects.create(
                provider=order.provider,
                order=order,
                
                type=exception_type,
                date=order.working_date,
                start_time=order.working_start_time,
                end_time=order.end_time,
                reason=reason
            )
        return slot_exception

    @action(detail=True, methods=["get"])
    def accept(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order already {order.status}.")
        with transaction.atomic():
            order.status = OrderStatus.ACCEPT
            order.accepted_at = timezone.localtime(timezone.now())
            order.save()

            self.get_or_create_slot_exception(order, HelperSlotExceptionType.FREEZED)

            handle_log_engine(
                request=request, action="ACCEPT OFFER", status=LogStatus.SUCCESS, message="Accept the Custom Offer.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Accept the Custom Offer by Customer"
            )
            return Response(
                {
                    "status": True,
                    "message": "Order accept and awaiting for payment."
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["get"], url_path="pay-and-confirm")
    def pay_and_confirm(self, request, *args, **kwargs):
        order = self.get_object()
        try:
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
                    profile=UserDefault.CUSTOMER,
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

                self.get_or_create_slot_exception(order, HelperSlotExceptionType.BOOKED)

                handle_log_engine(
                    request=request, action="PAYMENT COMPLETE", status=LogStatus.SUCCESS, message="Payment Complete & Order Confirm", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                    notify=True, logify=True,
                    role=UserRole.USER, send_to=self.request.user, send_to_type=UserDefault.CUSTOMER
                )
                handle_log_engine(
                    request=request, action="PAYMENT COMPLETE", status=LogStatus.SUCCESS, message="Payment Complete & Order Confirm", entity=order,
                    notify=True, logify=False,
                    role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER
                )
                return Response(
                    {"status": True, "message": "Order pay and confirm!"},
                    status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="PAYMENT COMPLETE", status=LogStatus.FAILED, message=str(e),
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
            )

            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="propose-new-time")
    def propose_new_time(self, request, *args, **kwargs):
        order  = self.get_object()
        with transaction.atomic():
            data = request.data
            action = data.pop("action", None)
            if action == "create":
                serializer = ProposeNewTimeSerializer(data=request.data, context={"order": order})
            elif action == "update":
                serializer = ProposeNewTimeActionSerializer(data=request.data)
            else:
                raise Exception("Action not mention!")
            serializer.is_valid(raise_exception=True)
            serializer.save(order=order, profile_type=UserDefault.CUSTOMER)

            self.get_or_create_slot_exception(order, HelperSlotExceptionType.BOOKED)
            
            handle_log_engine(
                request=request, action="PROPOSE NEW TIME", status=LogStatus.SUCCESS, message="Send Propose New Time for Changes Time", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Received Propose New Time for Changes Time."
            )
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
        message = data.get("message", None)
        if message is None:
            raise ValueError("Cancellation Reason/Message must be needed.")
        
        with transaction.atomic():
            if order.status in [OrderStatus.PENDING, OrderStatus.ACCEPT] and order.payment_status == OrderPaymentStatus.UNPAID:
                order.status = OrderStatus.CANCELLED
                order.payment_status = OrderPaymentStatus.CANCELLED
                response_message = "Order Cancelled"
            elif order.status == OrderStatus.CANCELLATION_REQUEST:
                return Response(
                    {
                        "status": False,
                        "message": "Cancellation Request already Send!"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            elif order.status in [OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS] and order.payment_status == OrderPaymentStatus.PAID:
                order.status = OrderStatus.CANCELLATION_REQUEST
                OrderChangesRequest.objects.create(
                    order=order,
                    request_by=UserDefault.CUSTOMER,
                    status=OrderChangesRequestStatus.NO_RESPONSE,
                    changes_type=ChangesRequestType.CANCEL,
                    changes_data={
                        "message": message
                    }
                )
                response_message = "Order Cancellation Request Send!"
            else:
                return Response(
                    {
                        "status": False,
                        "message": f"Order already {order.status}"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            order.save()

            handle_log_engine(
                request=request, action="ORDER CANCELLATION REQUEST", status=LogStatus.SUCCESS, message="Send Cancel Request for Cancel This Order", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )
    
    @action(detail=True, methods=["post"], url_path="cancel-accept")
    def cancellation_accept(self, request, *args, **kwargs):
        order = self.get_object()
        data = request.data

        # post data----
        request_id = data.get("changes_request_id", None)
        action = data.get("action", None)

        # data validation----
        if request_id is None:
            raise ValueError("Changes Request must be needed!")
        elif action is None:
            raise ValueError("Changes action must be needed!")
        elif not OrderChangesRequest.objects.filter(pk=request_id).exists():
            raise ValueError("Wrong Request ID.")
        
        # get refund amount----
        def get_refund_amount(order):
            return order.amount
        
        # user validation----
        changes_request = OrderChangesRequest.objects.get(pk=request_id)
        if changes_request.request_by == UserDefault.CUSTOMER:
            raise Exception("You can't perform this action")
        
        # use logic---
        with transaction.atomic():
            if action.upper() == OrderChangesRequestStatus.ACCEPT:
                changes_request.status = OrderChangesRequestStatus.ACCEPT
                changes_request.save()
                
                Order.objects.filter(pk=order.id).update(
                    status=OrderStatus.REFUND_REQUEST,
                    payment_status=OrderPaymentStatus.REFUND
                )
                OrderRefundRequest.objects.create(
                    order=order,
                    customer=order.customer,
                    reason=changes_request.changes_data.get("message", None),
                    order_amount=order.amount,
                    refund_amount=get_refund_amount(order)
                )
                HelperSlotException.objects.filter(order=order).update(is_active=False)
                response_message = "Order Cancelled Confirm & Refund Processing!"

                handle_log_engine(
                    request=request, action="CANCELLATION CONFIRM", status=LogStatus.SUCCESS, message="Order Cencellation Request Confirm By Customer.", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                    notify=True, logify=True,
                    role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Order Cencellation Request Confirm By Customer."
                )
            elif action.upper() in [OrderChangesRequestStatus.DECLINED, "REJECT"]:
                changes_request.status = OrderChangesRequestStatus.DECLINED
                changes_request.save()
                response_message = "Order Cancellation Declined!"

                handle_log_engine(
                    request=request, action="CANCELLATION REJECTED", status=LogStatus.SUCCESS, message="Order Cencellation Request Rejected By Customer.", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                    notify=True, logify=True,
                    role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Order Cencellation Request Rejected By Customer."
                )
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="give-feedback")
    def give_feedback(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            serializer = ReviewAndRatingSerializer(data=request.data, context={"order": order, "send_by": UserDefault.CUSTOMER, "request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            handle_log_engine(
                request=request, action="SEND FEEDBACK", status=LogStatus.SUCCESS, message="Send Feedback with this Order.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.provider.user, send_to_type=UserDefault.PROVIDER, notification_message="Received Feedback with this Order."
            )
            return Response(
                {
                    "status": True,
                    "message": "Thanks for your feedback!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="SEND FEEDBACK", status=LogStatus.FAILED, message="Failed to Send Feedback with this Order.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="POST METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Post Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
        )
        return Response(
            {
                "status": True,
                "message": "Create method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="UPDATE METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Update Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
        )
        return Response(
            {
                "status": True,
                "message": "Update method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="DELETE METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Delete Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.CUSTOMER
        )
        return Response(
            {
                "status": True,
                "message": "Delete method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

class ProviderOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPagination

    def get_serializer_context(self):
        return {"request": self.request, "profile_type": UserDefault.PROVIDER, "order": self.get_object() or None}

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

            handle_log_engine(
                request=request, action="COUNTER OFFER SEND", status=LogStatus.SUCCESS, message="Send Counter Offer from Provider.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Received Counter Offer from Provider"
            )
            return Response(
                {
                    "status": True,
                    "message": "Counter Offer Sent"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="COUNTER OFFER SEND", status=LogStatus.FAILED, message="Failed to Send Counter Offer.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
    
    def get_or_create_slot_exception(self, order, exception_type):
        if not (order.provider and order.working_date and order.working_start_time):
            return None
        reason=f"{exception_type} via order"
        if HelperSlotException.objects.filter(order=order).exists():
            slot_exception = HelperSlotException.objects.filter(order=order).first()
            slot_exception.type = exception_type
            slot_exception.date = order.working_date
            slot_exception.start_time = order.working_start_time
            slot_exception.end_time = order.end_time
            slot_exception.reason = reason
            slot_exception.save()
        else:
            slot_exception = HelperSlotException.objects.create(
                provider=order.provider,
                order=order,
                
                type=exception_type,
                date=order.working_date,
                start_time=order.working_start_time,
                end_time=order.end_time,
                reason=reason
            )
        return slot_exception

    @action(detail=True, methods=["get"])
    def accept(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order already {order.status}.")
        with transaction.atomic():
            order.status = OrderStatus.ACCEPT
            order.accepted_at = timezone.localtime(timezone.now())
            order.save()

            self.get_or_create_slot_exception(order, HelperSlotExceptionType.FREEZED)

            handle_log_engine(
                request=request, action="ACCEPT OFFER", status=LogStatus.SUCCESS, message="Accept the Custom Offer.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Accept the Custom Offer by Provider"
            )
            return Response(
                {
                    "status": True,
                    "message": "Order accept and awaiting for payment."
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="set-work-hour")
    def set_work_hour(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            with transaction.atomic():
                serializer = SetHourSerializer(data=request.data, context={"order": order})
                serializer.is_valid(raise_exception=True)
                serializer.save(order=order)

                self.get_or_create_slot_exception(order, HelperSlotExceptionType.BOOKED)

                handle_log_engine(
                    request=request, action="SET WORK HOUR", status=LogStatus.SUCCESS, message="Set Work Hour.", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
                )
                return Response(
                    {
                        "status": True,
                        "message": f"{serializer.validated_data.get("set_hour")} Hour Set for complete the work!"
                    }, status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="SET WORK HOUR", status=LogStatus.FAILED, message="Failed to Set Work Hour.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["post"], url_path="propose-new-time")
    def propose_new_time(self, request, *args, **kwargs):
        order = self.get_object()
        with transaction.atomic():
            data = request.data
            action = data.pop("action", None)
            if action == "create":
                serializer = ProposeNewTimeSerializer(data=request.data, context={"order": order})
            elif action == "update":
                serializer = ProposeNewTimeActionSerializer(data=request.data)
            else:
                raise Exception("Action not mention!")
            serializer.is_valid(raise_exception=True)
            serializer.save(order=order, profile_type=UserDefault.PROVIDER)

            self.get_or_create_slot_exception(order, HelperSlotExceptionType.BOOKED)

            handle_log_engine(
                request=request, action="PROPOSE NEW TIME", status=LogStatus.SUCCESS, message="Send Propose New Time for Changes Time", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Received Propose New Time for Changes Time."
            )
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
        message = data.get("message", None)
        if message is None:
            raise ValueError("Cancellation Reason/Message must be needed.")
        
        with transaction.atomic():
            if order.status in [OrderStatus.PENDING, OrderStatus.ACCEPT] and order.payment_status == OrderPaymentStatus.UNPAID:
                order.status = OrderStatus.CANCELLED
                order.payment_status = OrderPaymentStatus.CANCELLED
                response_message = "Order Cancelled"
            elif order.status == OrderStatus.CANCELLATION_REQUEST:
                return Response(
                    {
                        "status": False,
                        "message": "Cancellation Request already Send!"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            elif order.status in [OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS] and order.payment_status == OrderPaymentStatus.PAID:
                order.status = OrderStatus.CANCELLATION_REQUEST
                OrderChangesRequest.objects.create(
                    order=order,
                    request_by=UserDefault.PROVIDER,
                    status=OrderChangesRequestStatus.NO_RESPONSE,
                    changes_type=ChangesRequestType.CANCEL,
                    changes_data={
                        "message": message
                    }
                )
                response_message = "Order Cancellation Request Send!"
            else:
                return Response(
                    {
                        "status": False,
                        "message": f"Order already {order.payment_status}"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            order.save()

            handle_log_engine(
                request=request, action="ORDER CANCELLATION REQUEST", status=LogStatus.SUCCESS, message="Send Cancel Request for Cancel This Order", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="cancel-accept")
    def cancellation_accept(self, request, *args, **kwargs):
        order = self.get_object()
        data = request.data

        # post data----
        request_id = data.get("changes_request_id", None)
        action = data.get("action", None)

        # data validation----
        if request_id is None:
            raise ValueError("Changes Request must be needed!")
        elif action is None:
            raise ValueError("Changes action must be needed!")
        elif not OrderChangesRequest.objects.filter(pk=request_id).exists():
            raise ValueError("Wrong Request ID.")
        
        # get refund amount----
        def get_refund_amount(order):
            return order.amount
        
        # user validation----
        changes_request = OrderChangesRequest.objects.get(pk=request_id)
        if changes_request.request_by == UserDefault.PROVIDER:
            raise Exception("You can't perform this action")
        
        # use logic---
        with transaction.atomic():
            if action.upper() == OrderChangesRequestStatus.ACCEPT:
                changes_request.status = OrderChangesRequestStatus.ACCEPT
                changes_request.save()

                Order.objects.filter(pk=order.id).update(
                    status=OrderStatus.REFUND_REQUEST,
                    payment_status=OrderPaymentStatus.REFUND
                )
                OrderRefundRequest.objects.create(
                    order=order,
                    customer=order.customer,
                    reason=changes_request.changes_data.get("message", None),
                    order_amount=order.amount,
                    refund_amount=get_refund_amount(order)
                )
                HelperSlotException.objects.filter(order=order).update(is_active=False)
                response_message = "Order Cancelled Confirm & Refund Processing!"

                handle_log_engine(
                    request=request, action="CANCELLATION CONFIRM", status=LogStatus.SUCCESS, message="Order Cencellation Request Confirm By Provider.", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                    notify=True, logify=True,
                    role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Order Cencellation Request Confirm By Provider."
                )
            elif action.upper() in [OrderChangesRequestStatus.DECLINED, "REJECT"]:
                changes_request.status = OrderChangesRequestStatus.DECLINED
                changes_request.save()
                response_message = "Order Cancellation Declined!"

                handle_log_engine(
                    request=request, action="CANCELLATION REJECTED", status=LogStatus.SUCCESS, message="Order Cencellation Request Rejected By Provider.", entity=order,
                    perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                    notify=True, logify=True,
                    role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Order Cencellation Request Rejected By Provider."
                )
            return Response(
                {
                    "status": True,
                    "message": response_message
                }, status=status.HTTP_200_OK
            )

    @action(detail=True, methods=["post"], url_path="start-work")
    def start_work(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            if order.status != OrderStatus.CONFIRM:
                raise ValueError("Order must be confirmed!")
            serializer = StartWorkSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.work_start(order=order)
            
            handle_log_engine(
                request=request, action="START WORK", status=LogStatus.SUCCESS, message="Start work to complete.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    "status": True,
                    "message": "Work Started!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}

            handle_log_engine(
                request=request, action="START WORK", status=LogStatus.FAILED, message="Failed to Start work to complete.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            if self.get_object().status == OrderStatus.COMPLETED:
                raise ValueError("Order already complete")
            elif self.get_object().status != OrderStatus.IN_PROGRESS:
                raise ValueError("Order must be in progress!")
            
            serializer = CompleteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.complete(order=self.get_object())

            handle_log_engine(
                request=request, action="COMPLETE ORDER", status=LogStatus.SUCCESS, message="Mark Complete the order by OTP.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER
            )
            return Response(
                {
                    "status": True,
                    "message": "Work Complete!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="COMPLETE ORDER", status=LogStatus.FAILED, message="Failed to Mark Complete the order.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"], url_path="give-feedback")
    def give_feedback(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            serializer = ReviewAndRatingSerializer(data=request.data, context={"order": order, "send_by": UserDefault.PROVIDER, "request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            handle_log_engine(
                request=request, action="SEND FEEDBACK", status=LogStatus.SUCCESS, message="Send Feedback with this Order.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER,
                notify=True, logify=True,
                role=UserRole.USER, send_to=order.customer.user, send_to_type=UserDefault.CUSTOMER, notification_message="Received Feedback with this Order."
            )
            return Response(
                {
                    "status": True,
                    "message": "Thanks for your feedback!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            handle_log_engine(
                request=request, action="SEND FEEDBACK", status=LogStatus.FAILED, message="Failed to Send Feedback with this Order.", entity=order,
                perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
            )
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="POST METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Post Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
        )
        return Response(
            {
                "status": True,
                "message": "Post method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="UPDATE METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Update Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
        )
        return Response(
            {
                "status": True,
                "message": "Update method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        handle_log_engine(
            request=request, action="DELETE METHOD NOT ALLOWED", status=LogStatus.FAILED, message="Delete Method perform not allowed.",
            perform_user=self.request.user, perform_user_type=UserDefault.PROVIDER
        )
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

    def get_profile_type(self):
        return self.request.headers.get("profile-type", None)

    def get_queryset(self):
        if self.request.user.role == UserRole.USER:
            pt = PaymentTransaction.objects.filter(
                user=self.request.user
            ).filter(
                Q(type=PaymentTransactionType.CREDIT) | Q(type=PaymentTransactionType.DEBIT)
            )
            if self.get_profile_type() and self.get_profile_type().upper() in UserDefault.values:
                pt.filter(
                    profile=self.get_profile_type().upper()
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


    
