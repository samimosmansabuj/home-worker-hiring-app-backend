from .models import SignUpSlider, CustomerScreenSlide
from .site_serializer import SignUpSliderSerializer, CustomerScreenSlideSerializer, AdminWalletSerializer
from rest_framework import views
from find_worker_config.utils import UpdateModelViewSet, UpdateReadOnlyModelViewSet
from find_worker_config.permissions import IsAdminWritePermissionOnly, ForAdminProfile
from task.models import AdminWallet, PaymentTransaction
from rest_framework.response import Response

# SignUp Slider Views===============================
class SignUpSliderViewset(UpdateModelViewSet):
    queryset = SignUpSlider.objects.all()
    serializer_class = SignUpSliderSerializer
    permission_classes = [IsAdminWritePermissionOnly]

class CustomerScreenSlideViewset(UpdateModelViewSet):
    queryset = CustomerScreenSlide.objects.all()
    serializer_class = CustomerScreenSlideSerializer
    permission_classes = [IsAdminWritePermissionOnly]

class AdminWalletViews(views.APIView):
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



