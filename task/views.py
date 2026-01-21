from django.shortcuts import render
from .serializers import ServiceCategorySerializer, OrderSerializer, OrderRequestSerializer
from find_worker_config.utils import UpdateModelViewSet
from .models import ServiceCategory, Order, OrderRequest
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, viewsets
from find_worker_config.permissions import IsAuthenticatedForWrite, IsCustomer, IsServiceProvider, IsAdminWritePermissionOnly, IsServicePostCustomerGetOnly, IsCustomerPostServiceGetOnly
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault
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

class OrderViewSets(UpdateModelViewSet):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_user(self):
        return self.request.user
    
    def get_order(self, pk):
        return Order.objects.get(pk=pk)
    
    def get_order_request(self, pk):
        return OrderRequest.objects.get(pk=pk)
    
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
                            OrderStatus.HIRIED,
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
        elif order_type == "all":
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
                            OrderStatus.HIRIED,
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
            # order = (
            #     Order.objects
            #     .select_related("category", "provider")
            #     .prefetch_related("order_requests")
            #     .filter(
            #         Q(
            #             status__in=[
            #                 OrderStatus.PENDING,
            #                 OrderStatus.ACTIVE
            #             ]
            #         )
            #     )
            #     .distinct()
            # )
        else:
            order = (
                Order.objects
                .select_related("category", "provider")
                .prefetch_related("order_requests")
                .filter(
                    Q(
                        order_requests__provider=user.hasServiceProviderProfile,
                        status__in=[
                            OrderStatus.ACTIVE,
                            OrderStatus.ACCEPT,
                            OrderStatus.HIRIED,
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
        else:
            # raise Exception("Profile Type must be set in headers.")
            return self.customer_get_queryset()
    
    # =============== Get QuerySet ===============
    # ============================================
    
    @action(detail=True, methods=["post", "get"], url_path="send-request")
    def send_request(self, request, *args, **kwargs):
        if request.method == "POST":
            try:
                order = self.get_order(self.kwargs.get("pk"))
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
            order = self.get_order(self.kwargs.get("pk"))
            user = self.get_user()
            profile_type = self.request.headers.get("profile-type", "")

            if order.customer == user.hasCustomerProfile:
                get_response = OrderRequestSerializer(order.order_requests.all(), many=True).data
            elif user.role == UserRole.ADMIN:
                get_response = OrderRequestSerializer(order.order_requests.all(), many=True).data
            elif profile_type.upper() == UserDefault.PROVIDER and user.hasServiceProviderProfile:
                order_requests = order.order_requests.all()
                order_request = self.check_provider_in_request(user.hasServiceProviderProfile, order_requests)
                if order_request:
                    get_response = OrderRequestSerializer(order_request).data
                else:
                    get_response = "You have no request for this order!"
            else:
                get_response = "You have no request for this order!"
            return Response(
                {
                    "status": True,
                    "data": get_response
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    "status": False,
                    "message": f"{request.method} Not allowed"
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
    
    def check_provider_in_request(self, provider: object, order_requests: queryset):
        for order_request in order_requests:
            if order_request.provider_id == provider.id:
                return order_request
        return  None
    
    def isCustomerObjectUser(self, user1, user2):
        if user1 != user2:
            raise PermissionError("You do not have permission to perform this action.")

    @action(detail=True, methods=["post", "get"], url_path=r"send-request/(?P<request_id>\d+)")
    def send_request_action(self, request, *args, **kwargs):
        order_request = self.get_order_request(self.kwargs.get("request_id"))
        order = self.get_order(self.kwargs.get("pk"))
        user = self.get_user()
        if request.method == "POST":
            self.isCustomerObjectUser(order.customer.user, user)
            data = request.data
            status_action = data.get("status_action")

            # now start coding ...---------------------------------------------------------------------
            return Response(
                {
                    "status": True,
                    "message": "Send Request Action Working!"
                }, status=status.HTTP_200_OK
            )
        elif request.method == "GET":
            return Response(
                {
                    "status": True,
                    "message": "Send Request Action Working!"
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



# ==============================================================================================
# ==========================For User Start=================================
# class ServiceTaskViewSet(UpdateModelViewSet):
#     serializer_class = ServiceTaskForUserSerializer
#     permission_classes = [IsCustomer]
    
#     def get_queryset(self):
#         return ServiceTask.objects.select_related(
#             "category",
#         ).prefetch_related(
#             "requests"
#         ).filter(customer=self.request.user)
    
#     def perform_update(self, serializer):
#         push_notification(
#             user_id=self.request.user.id,
#             data={
#                 "type": "TASK_UPDATED",
#                 "message": "Your job has been updated"
#             }
#         )
#         return super().perform_update(serializer)

#     @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated])
#     def requests(self, request, pk=None):
#         task = self.get_object()
#         qs = task.requests.select_related("provider")

#         serializer = JobRequestSerializer(qs, many=True)
#         return Response(serializer.data)

# ==========================For User End=================================
# ==============================================================================================



# class ServicePrototypeViewSet(UpdateModelViewSet):
#     serializer_class = ServicePrototypeReadSerializer
#     permission_classes = [IsAuthenticatedForWrite, IsServiceProvider]

#     def get_serializer_class(self):
#         if self.request.method in ["POST", "PUT", "PATCH"]:
#             return ServicePrototypeWriteSerializer
#         return ServicePrototypeReadSerializer

#     def get_queryset(self):
#         return ServicePrototype.objects.select_related(
#             "service_provider",
#             "category"
#         ).filter(service_provider=self.request.user)

#     def perform_create(self, serializer):
#         serializer.save(service_provider=self.request.user)

# class TaskRequestViewSet(UpdateModelViewSet):
#     serializer_class = TaskRequestReadSerializer
#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.request.method in ["POST", "PUT", "PATCH"]:
#             return TaskRequestReadSerializer
#         return TaskRequestWriteSerializer

#     def get_queryset(self):
#         user = self.request.user
#         if user.role == "PROVIDER":
#             return TaskRequest.objects.select_related(
#                 "task", "provider"
#             ).filter(provider=user)

#         return TaskRequest.objects.select_related(
#             "task", "provider"
#         ).filter(task__customer=user)

#     def perform_create(self, serializer):
#         serializer.save(provider=self.request.user)


