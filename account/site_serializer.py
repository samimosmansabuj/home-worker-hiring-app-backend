from rest_framework import serializers
from .models import SignUpSlider, CustomerScreenSlide
from task.models import AdminWallet, PaymentTransaction

# SignUp Slider Serializers===============================
class SignUpSliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUpSlider
        fields = "__all__"

class CustomerScreenSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerScreenSlide
        fields = "__all__"

class AdminWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminWallet
        fields = ["current_balance", "payment_balance", "hold_balance", "total_withdraw"]


