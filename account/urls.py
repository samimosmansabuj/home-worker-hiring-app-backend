from django.urls import path, include
from .views import (
    PasswordLoginViews, LoginOTPRequestView, LoginOTPVerifyView, SignUpOTPRequestView, SignUpOTPVerifyView, UserInfoView, UserAddressViews, SignUpViews, UpdateTokenVerifyView, UpdateTokenRefreshView,ChangePasswordView, PasswordResetRequestView, PasswordResetConfirmView, UserSignUpOTPVerifyView, ProviderVerificationViews, GoogleLoginAPIView, HelperListViewset, CustomerPaymentMethodViewSet, ProviderPayoutMethodViewSet, UserDefaultLanguage, MyReferralViewSet, MyVoucherViewSet, ApplyVoucherView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"address", UserAddressViews, basename="user_address")
router.register(r"helper", HelperListViewset, basename="helper")
router.register(r'customer/payment-methods', CustomerPaymentMethodViewSet, basename='customer-payment')
router.register(r'provider/payout-methods', ProviderPayoutMethodViewSet, basename='provider-payout')
router.register(r"my-referrals", MyReferralViewSet, basename="my-referrals")
router.register(r"my-vouchers", MyVoucherViewSet, basename="my-vouchers")



urlpatterns = [
    # Auth Route For All User--------------
    path("token/auth/", PasswordLoginViews.as_view(), name="user_login"),
    path("token/otp/request/", LoginOTPRequestView.as_view(), name="login_otp_send"),
    path("token/otp/verify/", LoginOTPVerifyView.as_view(), name="login_otp_verify"),
    path("token/verify/", UpdateTokenVerifyView.as_view(), name="token-verify"),
    path("token/refresh/", UpdateTokenRefreshView.as_view(), name="token-refresh"),
    # Password Change & Reset---------------
    path("auth/password/change/", ChangePasswordView.as_view(), name="password-change"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password/reset-confirm/", PasswordResetConfirmView.as_view(), name="password-confirm"),
    # User Registration Route---------------
    # path("signup/otp/request/", SignUpOTPRequestView.as_view(), name="signup_otp_send"),
    # path("signup/otp/verify/", SignUpOTPVerifyView.as_view(), name="signup_otp_verify"),
    path("auth/signup/", SignUpViews.as_view(), name="signup"),
    path("auth/signup/verify/", UserSignUpOTPVerifyView.as_view(), name="signup-verify"),

    # Social Auth Login Start--------------
    path("auth/token/google/", GoogleLoginAPIView.as_view(), name="google-auth"),
    path("auth/token/apple/", GoogleLoginAPIView.as_view(), name="apple-auth"),
    # Social Auth Login End--------------
    
    path("current-user/", UserInfoView.as_view(), name="current_user_info"),
    path("user/", include(router.urls)),
    path("provider-verification/", ProviderVerificationViews.as_view(), name="provider-verification"),
    path("user/language/", UserDefaultLanguage.as_view(), name="user-language"),

    # Referral & Voucher Section---------
    path("vouchers/apply/", ApplyVoucherView.as_view(), name="apply-voucher"),
]

