from .models import SignUpSlider, CustomerScreenSlide
from .site_serializer import SignUpSliderSerializer, CustomerScreenSlideSerializer
from find_worker_config.utils import UpdateModelViewSet
from find_worker_config.permissions import IsAdminWritePermissionOnly

# SignUp Slider Views===============================
class SignUpSliderViewset(UpdateModelViewSet):
    queryset = SignUpSlider.objects.all()
    serializer_class = SignUpSliderSerializer
    permission_classes = [IsAdminWritePermissionOnly]

class CustomerScreenSlideViewset(UpdateModelViewSet):
    queryset = CustomerScreenSlide.objects.all()
    serializer_class = CustomerScreenSlideSerializer
    permission_classes = [IsAdminWritePermissionOnly]


