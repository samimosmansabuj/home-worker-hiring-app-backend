from django.shortcuts import render, get_object_or_404
from .serializers import ServiceCategorySerializer, OrderSerializer, OrderRequestSerializer, OrderRequestSerializerForOrder, ReviewAndRatingSerializer
from find_worker_config.utils import UpdateModelViewSet
from .models import ServiceCategory, Order, OrderRequest, ReviewAndRating
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from find_worker_config.permissions import ForProviderProfile, IsAdminWritePermissionOnly, HasCustomerProfileSafeModeTypeHeader, ForCustomerProfile, ForAdminProfile
from chat_notify.utils import push_notify_all, push_notify_role, push_notification
from find_worker_config.model_choice import UserRole, OrderStatus, UserDefault, OrderRequestStatus, OrderPaymentStatus
from django.db.models import Q
from rest_framework import views
from .services import OrderService

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
    permission_classes = [IsAuthenticated, HasCustomerProfileSafeModeTypeHeader]
    
    def get_user(self):
        profile_type = self.request.headers.get("profile-type", "")
        return self.request.user



class CustomerOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [ForCustomerProfile]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user.hasCustomerProfile
        ).prefetch_related("order_requests")

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
                OrderRequest.objects.filter(
                    order=order
                ).exclude(
                    provider=order_request.provider
                ).update(status=OrderRequestStatus.PENDING)
                order_request.status = OrderRequestStatus.PENDING
                order_request.save(update_fields=["status"])
                order.status=OrderStatus.ACTIVE
                order.amount=0
                order.save(update_fields=["status", "amount"])
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
            order_request.status = OrderRequestStatus.REJECTED
            order_request.save(update_fields=["status"])
        elif action_status == OrderRequestStatus.ACCEPTED:
            amount = request.data.get("amount", None)
            if not amount:
                raise Exception("Final Amount Must be Set.")
            OrderService.accept_order(order, order_request, float(amount))
        return Response({"status": True, "message": "Order Accepted"})
    
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
            if order.status == OrderStatus.ACCEPT and order.payment_status == OrderPaymentStatus.UNPAID:
                order_request = self.get_accepted_order_request(order, kwargs.get("request_id", None))
                

                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\
                # Here Code for Payment Process and Build Logic
                # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\

                return Response(
                    {
                        "status": True,
                        "message": "Order payment complete!"
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "status": False,
                        "message": "Not allowed."
                    }
                )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )



    def destroy(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            if order.status != OrderStatus.ACTIVE:
                raise PermissionDenied("Order cannot be deleted at this stage.")
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


class ProviderOrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, ForProviderProfile]

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

class AdminOrderViewSet(UpdateModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, ForAdminProfile]









    
