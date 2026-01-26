from rest_framework import serializers
from .models import SignUpSlider, CustomerScreenSlide

# SignUp Slider Serializers===============================
class SignUpSliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUpSlider
        fields = "__all__"

class CustomerScreenSlideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerScreenSlide
        fields = "__all__"

