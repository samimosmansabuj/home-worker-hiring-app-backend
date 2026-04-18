from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Ticket, SignUpSlider, CustomerScreenSlide
from .serializers import TicketSerializer, TicketReplySerializer, TicketStatusUpdateSerializer, AdminWalletSerializer, SignUpSliderSerializer, CustomerScreenSlideSerializer
from find_worker_config.model_choice import UserRole
from find_worker_config.utils import UpdateModelViewSet, LogActivityModule
from django.db import transaction
from rest_framework.views import APIView
from task.models import AdminWallet
from find_worker_config.permissions import IsAdminWritePermissionOnly

# -------------------
# Ticket ViewSet
class TicketViewSet(UpdateModelViewSet):
    queryset = Ticket.objects.all().order_by("-created_at")
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_user_profile_type(self):
        if self.request.user.role == UserRole.ADMIN:
            raise Exception("Admin can't create tickets!")
        profile_type = self.request.headers.get("profile-type")
        if not profile_type:
            raise Exception("Profile Type Missing")
        return profile_type.upper()

    def get_queryset(self):
        user = self.request.user
        profile_type = self.request.headers.get("profile-type", "").upper()
        tickets = Ticket.objects.all().order_by("-created_at")

        if user.role == UserRole.USER and profile_type:
            return tickets.filter(user=user, user_profile_type=profile_type)
        elif user.role == UserRole.USER:
            return tickets.filter(user=user)
        elif user.role == UserRole.ADMIN:
            return tickets
        return None

    def get_serializer_class(self):
        if self.action == "reply":
            return TicketReplySerializer
        elif self.action in ["update_status"]:
            return TicketStatusUpdateSerializer
        return TicketSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        user_profile_type = self.get_user_profile_type()
        with transaction.atomic():
            instance = serializer.save(user=user, user_profile_type=user_profile_type)
            self.create_log("Create a ticket", instance, for_notify=True)
            return instance
    
    # -------------------
    # Log Create & Notify
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
    # -------------------

    # -------------------
    # Reply to a ticket
    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketReplySerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save(ticket=ticket)
                return Response(
                    {
                        "status": True,
                        "data": serializer.data
                    }, status=status.HTTP_201_CREATED
                )
        return Response(
            {
                "status": False,
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST
        )
    # -------------------

    # -------------------
    # Close a ticket (only admin or owner)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        ticket = self.get_object()
        if not (request.user.role == UserRole.ADMIN or ticket.user == request.user):
            return Response({"detail": "Not allowed"}, status=status.HTTP_403_FORBIDDEN)
        ticket.status = "closed"
        ticket.save()
        serializer = self.get_serializer(ticket)
        return Response(
            {
                "status": True,
                "data": serializer.data
            }
        )
    # -------------------
# -------------------


# -------------------
# Admin Wallet Views
class AdminWalletViews(APIView):
    def get_wallet(self):
        wallet, _ = AdminWallet.objects.get_or_create()
        return wallet
    
    def get(self, request):
        serializer = AdminWalletSerializer(self.get_wallet())
        return Response(
            {
                "status": True,
                "data": serializer.data
            }
        )
# -------------------


# -------------------
# Singup Slider Viewsets
class SignUpSliderViewset(UpdateModelViewSet):
    queryset = SignUpSlider.objects.all()
    serializer_class = SignUpSliderSerializer
    permission_classes = [IsAdminWritePermissionOnly]
# -------------------

# -------------------
# Customer Screen Slider Viewsets
class CustomerScreenSlideViewset(UpdateModelViewSet):
    queryset = CustomerScreenSlide.objects.all()
    serializer_class = CustomerScreenSlideSerializer
    permission_classes = [IsAdminWritePermissionOnly]
# -------------------

