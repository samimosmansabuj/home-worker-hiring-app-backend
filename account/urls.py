from django.urls import path, include
from .views import (
    GetMyReferralCodeView, HelperWeeklyAvailabilityViewSet, MyActivityViews, NextJobOrdersView, ProviderEarningsTransactionsView, ProviderEarningsView, RecommendationHelperViewSet, ReviewAndRatingProfileViewSet, UserAddressViews, ProviderVerificationViews, CustomerPaymentMethodViewSet, ProviderPayoutMethodViewSet, UserDefaultLanguage, MyReferralViewSet, MyVoucherViewSet, ApplyVoucherView, ProviderAddressUpdateView, CurrentUserInfoView, CurrentUserHelperView, CreateUserHelperView, SaveHelperProfileViews
)
from .auth_views import (
    PasswordLoginViews, LoginOTPRequestView, LoginOTPVerifyView, SignUpViews, UpdateTokenVerifyView, UpdateTokenRefreshView,ChangePasswordView, PasswordResetRequestView, PasswordResetConfirmView, UserSignUpOTPVerifyView, GoogleLoginAPIView, SignUpOTPResend
)
from rest_framework.routers import DefaultRouter


# ============================================================================================================
router = DefaultRouter()
# user---------
router.register(r"address", UserAddressViews, basename="user_address")
router.register(r"reviews", ReviewAndRatingProfileViewSet, basename="user_review_rating")
# provider-----
router.register(r'provider/payout-methods', ProviderPayoutMethodViewSet, basename='provider-payout')
router.register(r'helper-weekly-availability', HelperWeeklyAvailabilityViewSet, basename='helper-weekly-availability')
# customer-----
router.register(r'customer/payment-methods', CustomerPaymentMethodViewSet, basename='customer-payment')
router.register(r'customer/save-helper', SaveHelperProfileViews, basename='customer-save-helper')
router.register(r"my-referrals", MyReferralViewSet, basename="my-referrals")
router.register(r"my-vouchers", MyVoucherViewSet, basename="my-vouchers")
router.register(r"recommended-helpers", RecommendationHelperViewSet, basename="my-recommended-helpers")
# ============================================================================================================



urlpatterns = [
    # ========================================================================================================
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
    path("auth/signup/resend/", SignUpOTPResend.as_view(), name="signup-otp-resend"),

    # Social Auth Login Start--------------
    path("auth/token/google/", GoogleLoginAPIView.as_view(), name="google-auth"),
    path("auth/token/apple/", GoogleLoginAPIView.as_view(), name="apple-auth"),
    # Social Auth Login End--------------
    # ========================================================================================================


    # Current User URL----------------------
    path("current-user/", CurrentUserInfoView.as_view(), name="current_user_info"),

    # Helper User Related API Views Start================================
    path("helper-profile/", CurrentUserHelperView.as_view(), name="user-helper-profile"),
    path("create-helper-profile/", CreateUserHelperView.as_view(), name="create-helper-profile"),
    path("provider-address-update/", ProviderAddressUpdateView.as_view(), name="provider-address-update"),
    path("provider-verification/", ProviderVerificationViews.as_view(), name="provider-verification"),
    path("provider/next-job-orders/", NextJobOrdersView.as_view(), name="next-job-orders"),
    path("provider/earnings-overview/", ProviderEarningsView.as_view(), name="provider-earnings-overview"),
    path("provider/earnings-transactions/", ProviderEarningsTransactionsView.as_view(), name="provider-earnings-transactions"),
    # path("helper-weekly-availability/", HelperWeeklyAvailabilityViewSet.as_view({'get': 'list', 'post': 'create'}), name="helper-weekly-availability"),
    

    path("user/language/", UserDefaultLanguage.as_view(), name="user-language"),
    path("user/", include(router.urls)),


    # Customer User Related API Views Start================================
    path("activity/", MyActivityViews.as_view(), name="my-activity"),
    path("my-referral-code/", GetMyReferralCodeView.as_view(), name="my-referral-code"),
    # Referral & Voucher Section---------
    path("vouchers/apply/", ApplyVoucherView.as_view(), name="apply-voucher"),
]

