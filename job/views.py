from django.shortcuts import render
from .serializers import CompleteSerializer, CounterSerializer, ProposeNewTimeActionSerializer, ProposeNewTimeSerializer, SetHourSerializer, OrderSerializerAll, StartWorkSerializer, ReviewAndRatingSerializer, CurrentUserHelperSerializer
from account.models import Address, User, ServiceProviderProfile
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from find_worker_config.utils import LogActivityModule, UpdateReadOnlyModelViewSet, UpdateModelViewSet, PaymentTransactionModule
from task.models import Order, OrderRefundRequest
from django.db import transaction
import requests
from rest_framework.exceptions import ValidationError, PermissionDenied
import os
from math import radians, cos, sin, asin, sqrt
from django.db.models import Q
from rest_framework.generics import CreateAPIView
from .paginations import HelperPagination
from find_worker_config.model_choice import UserDefault, OrderStatus, PaymentTransactionType, PaymentAction, OrderPaymentStatus
from rest_framework.decorators import action
from django.utils import timezone


# ============================================================
# Buyer/Helper List for Customer/Client===================
class HelperListViewset(UpdateReadOnlyModelViewSet):
    serializer_class = CurrentUserHelperSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HelperPagination

    def get_serializer_context(self):
        return {"request": self.request}
    
    def haversine(self, lat2, lon2):
        lon1, lat1, lon2, lat2 = map(
            radians, [self.user_lng, self.user_lat, lon2, lat2]
        )
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return round(6371 * c, 2)
    
    def get_map_distance(self,  lat2, lon2):
        api_key = os.getenv("GOOGLE_MAP_API_KEY")
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": f"{lat1},{lon1}",
            "destinations": f"{lat2},{lon2}",
            "key": api_key
        }
        response = requests.get(url, params=params)
        print("Google Maps API Response:", response.text)  # Debug log
        if response.status_code != 200:
            return None
        data = response.json()
        try:
            distance_text = data["rows"][0]["elements"][0]["distance"]["text"]
            distance_value = float(distance_text.replace(" km", "").replace(",", ""))
            return distance_value
        except (KeyError, IndexError, ValueError):
            return None

    def get_filter_data(self, queryset):
        # ---- Query Params ----
        q = self.request.query_params.get("q")
        category_id = self.request.query_params.get("category_id")
        distance_radius = self.request.query_params.get("distance_radius")
        budget = self.request.query_params.get("budget")
        min_rating = self.request.query_params.get("rating")
        availability = self.request.query_params.get("availability")

        # ---- Search Filter ----
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(details__icontains=q)
            )

        # ---- Category Filter ----
        if category_id:
            queryset = queryset.filter(
                service_category__id=category_id
            )

        # ---- Rating Filter ----
        if min_rating:
            queryset = queryset.filter(
                rating__gte=float(min_rating)
            )
        
        # ---- Availability ----
        if availability:
            queryset = queryset.filter(
                availability_status=availability
            )

        # ---- Budget ----
        if budget:
            queryset = queryset.filter(
                hourly_rate__lte=float(budget)
            )

        # ---- Distance Calculation (ALWAYS attach) ----
        helpers = []
        for helper in queryset:
            office = helper.office_location
            if not office or not office.lat or not office.lng:
                continue
            distance = self.haversine(office.lat, office.lng)
            # distance = self.get_map_distance(office.lat, office.lng)
            helper.distance_km = distance

            # ---- Distance Radius Filter ----
            if distance_radius:
                if distance <= float(distance_radius):
                    helpers.append(helper)
            else:
                helpers.append(helper)
        return helpers
    
    def get_queryset(self):
        user = self.request.user
        address = Address.objects.filter(user=user, is_default=True).first()
        if not address:
            return User.objects.none()
        self.user_lat = address.lat
        self.user_lng = address.lng

        return ServiceProviderProfile.objects.select_related(
            "user", "office_location"
        ).prefetch_related(
            "service_category"
        ).exclude(
            user=user
        )
    
    def get_sorting_queryset(self, queryset, sort_by):
        if sort_by == "rating":
            queryset.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "price":
            queryset.sort(key=lambda x: x.hourly_rate or 0)
        elif sort_by == "distance" or not sort_by:
            queryset.sort(key=lambda x: x.distance_km)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        helpers = self.get_filter_data(queryset)
        sort_by = request.query_params.get("sort_by")
        helpers = self.get_sorting_queryset(helpers, sort_by)

        page = self.paginate_queryset(helpers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(helpers, many=True)
        return Response({
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        office = instance.office_location
        if office or office.lat or office.lng:
            # self.get_map_distance(office.lat, office.lng) # use For Google API Destination
            instance.distance_km = self.haversine(office.lat, office.lng)
        serializer = self.get_serializer(instance)
        print("serializer: ", serializer.data)
        return self.perform_retrieve(serializer)

# Buyer/Helper List for Customer/Client===================
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


