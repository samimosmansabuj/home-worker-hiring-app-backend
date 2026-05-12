from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Ticket, SignUpSlider, CustomerScreenSlide
from .serializers import TicketSerializer, TicketReplySerializer, TicketStatusUpdateSerializer, AdminWalletSerializer, SignUpSliderSerializer, CustomerScreenSlideSerializer
from find_worker_config.model_choice import TicketSenderType, TicketStatus, TicketUserProfileType, UserRole, OrderStatus
from find_worker_config.utils import UpdateModelViewSet, LogActivityModule
from django.db import transaction
from rest_framework.views import APIView
from task.models import AdminWallet, PaymentTransaction, Order
from find_worker_config.permissions import IsAdminWritePermissionOnly

class DashboardAPIView(APIView):
    action_order = Order.objects.filter(
        status__in=[OrderStatus.ACTIVE, OrderStatus.ACCEPT, OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS]
    )
    
    def post(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Ok"
            }, status=status.HTTP_200_OK
        )


