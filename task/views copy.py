from django.shortcuts import render, get_object_or_404
from .serializers import ServiceCategorySerializer, OrderSerializer, OrderRequestSerializer, OrderRequestSerializerForOrder, ReviewAndRatingSerializer
from find_worker_config.utils import UpdateModelViewSet
from .models import ServiceCategory, Order, OrderRequest, ReviewAndRating
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from find_worker_config.permissions import IsAuthenticatedForWrite, IsCustomer, IsServiceProvider, IsAdminWritePermissionOnly, IsServicePostCustomerGetOnly, IsCustomerPostServiceGetOnly, HasCustomerProfileSafeModeTypeHeader, ForCustomerProfile, IsProvider, IsAdmin
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault, OrderRequestStatus
from django.db.models import Q
from rest_framework import views

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


class OrderViewMixing:
    def isCustomerObjectUser(self, user1, user2):
        if user1 != user2:
            raise PermissionDenied("You do not have permission to perform this action.")
    
    def check_provider_in_request(self, provider: object, order_requests: queryset):
        for order_request in order_requests:
            if order_request.provider_id == provider.id:
                return order_request
        return None

class OrderViewSets(UpdateModelViewSet, OrderViewMixing):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_user(self):
        return self.request.user
    
    def get_order(self, pk):
        return get_object_or_404(Order, pk=pk)
    
    def get_order_request(self, pk):
        return get_object_or_404(OrderRequest, pk=pk)
    
    # ============================================
    # =============== Get QuerySet ===============
    def provider_get_queryset(self):
        user = self.get_user()
        order_type = self.request.query_params.get("order_type")
        if order_type == "confirm-order":
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        order_requests__provider=user.hasServiceProviderProfile,
                        status__in=[
                            OrderStatus.CONFIRM,
                            OrderStatus.IN_PROGRESS,
                            OrderStatus.COMPLETED,
                            OrderStatus.PARTIAL_COMPLETE,
                            OrderStatus.CANCELLED,
                            OrderStatus.REFUND
                        ]
                    )
                )
                .distinct()
            )
        elif order_type == "request-order":
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        order_requests__provider=user.hasServiceProviderProfile,
                        status__in=[
                            OrderStatus.ACTIVE,
                            OrderStatus.ACCEPT
                        ]
                    )
                )
                .distinct()
            )
        elif order_type == "active-order":
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        status__in=[
                            OrderStatus.ACTIVE
                        ]
                    )
                )
                .distinct()
            )
        elif order_type == "all-order":
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        status__in=[
                            OrderStatus.ACTIVE
                        ]
                    )
                    |
                    Q(
                        order_requests__provider=user.hasServiceProviderProfile,
                        status__in=[
                            OrderStatus.ACCEPT,
                            OrderStatus.CONFIRM,
                            OrderStatus.IN_PROGRESS,
                            OrderStatus.COMPLETED,
                            OrderStatus.PARTIAL_COMPLETE,
                            OrderStatus.CANCELLED,
                            OrderStatus.REFUND
                        ]
                    )
                )
                .distinct()
            )
        else:
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        status__in=[
                            OrderStatus.ACTIVE
                        ]
                    )
                )
                .distinct()
            )
        return order
    
    def customer_get_queryset(self):
        user = self.get_user()
        return Order.objects.select_related(
            "category", "provider"
        ).prefetch_related(
            "order_requests"
        ).filter(
            customer=user.hasCustomerProfile
        )

    def admin_get_queryset(self):
        if self.request.user.role != UserRole.ADMIN:
            raise PermissionDenied("Only Admin User can Access.")
        return Order.objects.select_related(
            "category", "provider"
        ).prefetch_related(
            "order_requests"
        ).all()

    def get_queryset(self):
        profile_type = self.request.headers.get("profile-type", "")
        if profile_type.upper() == UserDefault.CUSTOMER:
            return self.customer_get_queryset()
        elif profile_type.upper() == UserDefault.PROVIDER:
            return self.provider_get_queryset()
        elif profile_type.upper() == UserRole.ADMIN:
            return self.admin_get_queryset()
        else:
            raise Exception("Profile Type must be set in headers.")
    
    # =============== Get QuerySet ===============
    # ============================================
    
    @action(detail=True, methods=["post", "get", "patch", "delete"], url_path="send-request")
    def send_request(self, request, *args, **kwargs):
        if request.method == "POST":
            try:
                order = self.get_object()
                # order = self.get_order(self.kwargs.get("pk"))
                request_serializer = OrderRequestSerializer(data=request.data, context={"request": request, "order": order})
                request_serializer.is_valid(raise_exception=True)
                request_serializer.save(order=order)
                return Response(
                    {
                        "status": True,
                        "message": "Request Succefully Send!",
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
        if request.method == "GET":
            order = self.get_object()
            user = self.get_user()
            profile_type = self.request.headers.get("profile-type", "").upper()

            if profile_type == UserDefault.CUSTOMER and order.customer == user.hasCustomerProfile:
                get_response = OrderRequestSerializerForOrder(order.order_requests.all(), many=True).data
            elif profile_type == UserRole.ADMIN and user.role == UserRole.ADMIN:
                get_response = OrderRequestSerializerForOrder(order.order_requests.all(), many=True).data
            elif profile_type == UserDefault.PROVIDER and user.hasServiceProviderProfile:
                order_requests = order.order_requests.all()
                order_request = self.check_provider_in_request(user.hasServiceProviderProfile, order_requests)
                if order_request:
                    get_response = OrderRequestSerializerForOrder(order_request).data
                else:
                    get_response = "You have no request for this order!"
            else:
                get_response = "No request for this order!"
            return Response(
                {
                    "status": True,
                    "data": get_response
                }, status=status.HTTP_200_OK
            )
        if request.method == "PATCH":
            try:
                order = self.get_object()
                order_request = OrderRequest.objects.filter(
                    order=order,
                    provider=self.get_user().hasServiceProviderProfile
                ).first()
                if not order_request:
                    raise Exception("You have not sent any request for this order.")
                if order_request.status == OrderRequestStatus.ACCEPTED:
                    raise Exception("Order Request Already Accepted.")
                if order.status != OrderStatus.ACTIVE:
                    raise Exception(f"Can't Update Your Request Right Now.")
                
                # budget = request.data.get("budget")
                # message = request.data.get("message")
                # if budget:
                #     order_request.budget = budget
                # if message:
                #     order_request.message = message
                # order_request.save(update_fields=["budget", "message"])
                update_fields = []
                if budget:
                    order_request.budget = budget
                    update_fields.append("budget")
                if message:
                    order_request.message = message
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
                order_request = OrderRequest.objects.get(
                    order=order,
                    provider=self.get_user().hasServiceProviderProfile
                )
                order_request.delete()
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
        else:
            return Response(
                {
                    "status": False,
                    "message": f"{request.method} Not allowed"
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    
    def update_accept_order(self, order, order_request):
        provier = order_request.provider
        order.provider = provier
        order.status = OrderStatus.ACCEPT
        order.save(update_fields=["status", "provider"])
        return True

    @action(detail=True, methods=["post", "get"], url_path=r"send-request/(?P<request_id>\d+)")
    def send_request_action(self, request, *args, **kwargs):
        request_id = self.kwargs.get("request_id")
        order = self.get_object()
        user = self.get_user()
        profile_type = self.request.headers.get("profile-type", "")
        if request.method == "POST":
            self.isCustomerObjectUser(order.customer.user, user)
            order_request = OrderRequest.objects.get(id=request_id, order=order)
            data = request.data
            status_action = data.get("status_action", "").upper()
            if status_action in (OrderRequestStatus.ACCEPTED, OrderRequestStatus.PENDING, OrderRequestStatus.REJECTED):
                order_request.status=status_action
                order_request.save(update_fields=["status"])
                if status_action == OrderRequestStatus.ACCEPTED:
                    self.update_accept_order(order, order_request)
            else:
                raise Exception("Wrong status input.")
            return Response(
                {
                    "status": True,
                    "message": OrderRequestSerializerForOrder(order_request).data
                }, status=status.HTTP_200_OK
            )
        elif request.method == "GET":
            if user == order.customer.user:
                order_request = OrderRequest.objects.get(id=request_id, order=order)
            elif not profile_type:
                raise Exception("Profile Type must be set in headers.")
            elif profile_type.upper() == UserDefault.PROVIDER:
                if not OrderRequest.objects.filter(id=request_id, order=order, provider=user.hasServiceProviderProfile).exists():
                    raise Exception("You have no send request for this order!")
                order_request = OrderRequest.objects.get(id=request_id, order=order, provider=user.hasServiceProviderProfile)
            return Response(
                {
                    "status": True,
                    "message": OrderRequestSerializerForOrder(order_request).data
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "status": False,
                    "message": f"{request.method} Not allowed"
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

class OrderRequestViewSets(UpdateModelViewSet):
    queryset = OrderRequest.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = OrderRequestSerializer





class ReviewAndRatingViewSets(UpdateModelViewSet):
    queryset = ReviewAndRating.objects.all()
    serializer_class = ReviewAndRatingSerializer
    permission_classes = [IsAuthenticated, HasCustomerProfileSafeModeTypeHeader]
    
    def get_user(self):
        profile_type = self.request.headers.get("profile-type", "")
        return self.request.user






from .services import OrderService

class CustomerOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user.hasCustomerProfile
        ).prefetch_related("order_requests")

    @action(detail=True, methods=["get"])
    def requests(self, request, pk=None):
        order = self.get_object()
        serializer = OrderRequestSerializerForOrder(
            order.order_requests.all(), many=True
        )
        return Response({"status": True, "data": serializer.data})

    @action(detail=True, methods=["post"], url_path="accept-request/(?P<request_id>\\d+)")
    def accept_request(self, request, pk=None, request_id=None):
        order = self.get_object()
        order_request = OrderRequest.objects.get(
            id=request_id,
            order=order
        )
        OrderService.accept_order(order, order_request)
        return Response({"status": True, "message": "Order Accepted"})


class ProviderOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsProvider]

    def get_queryset(self):
        return Order.objects.filter(
            order_requests__provider=self.request.user.hasServiceProviderProfile
        ).distinct()

    @action(detail=True, methods=["post"])
    def send_request(self, request, pk=None):
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
        return Response(
            {"status": True, "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["patch"])
    def update_request(self, request, pk=None):
        order = self.get_object()
        order_request = OrderRequest.objects.get(
            order=order,
            provider=request.user.hasServiceProviderProfile
        )
        serializer = OrderRequestSerializer(
            order_request, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": True, "data": serializer.data})    

class AdminOrderViewSet(UpdateModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsAdmin]









    
