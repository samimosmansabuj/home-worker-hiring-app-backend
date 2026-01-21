from django.urls import path, include
from .views import PasswordLoginViews, LoginOTPRequestView, LoginOTPVerifyView, SignUpOTPRequestView, SignUpOTPVerifyView, UserInfoView, UserAddressViews
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"address", UserAddressViews, basename="user_address")

urlpatterns = [
    path("token/auth/", PasswordLoginViews.as_view(), name="user_login"),
    path("token/otp/request/", LoginOTPRequestView.as_view(), name="login_otp_send"),
    path("token/otp/verify/", LoginOTPVerifyView.as_view(), name="login_otp_verify"),

    path("signup/otp/request/", SignUpOTPRequestView.as_view(), name="signup_otp_send"),
    path("signup/otp/verify/", SignUpOTPVerifyView.as_view(), name="signup_otp_verify"),

    
    path("current-user/", UserInfoView.as_view(), name="current_user_info"),
    path("user/", include(router.urls)),
]