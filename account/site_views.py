from .models import SignUpSlider, CustomerScreenSlide
from .site_serializer import SignUpSliderSerializer, CustomerScreenSlideSerializer, AdminWalletSerializer
from rest_framework import views
from find_worker_config.utils import UpdateModelViewSet, UpdateReadOnlyModelViewSet
from find_worker_config.permissions import IsAdminWritePermissionOnly, ForAdminProfile
from task.models import AdminWallet, PaymentTransaction
from rest_framework.response import Response
from find_worker_config.model_choice import UserLanguage

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

class UserDefaultLanguage(views.APIView):
    def get(self, request, *args, **kwargs):
        if request.session["language"]:
            return Response(
                {
                    "status": True,
                    "language": request.session["language"]
                }
            )
        elif request.user.is_authenticated:
            language = request.user.language
        else:
            language = UserLanguage.EN
        request.session["language"] = language
        return Response(
            {
                "status": True,
                "language": request.session["language"]
            }
        )
    
    def post(self, request):
        data = request.data
        lan = data.get("language" or UserLanguage.EN)
        if lan in [UserLanguage.EN, UserLanguage.ZH]:
            language = lan
        else:
            language = UserLanguage.EN
        request.session["language"] = language
        return Response(
            {
                "status": True,
                "language": request.session["language"]
            }
        )

