from django.urls import path, include
from .views import PasswordLoginViews, LoginOTPRequestView, LoginOTPVerifyView, SignUpOTPRequestView, SignUpOTPVerifyView, UserInfoView, UserAddressViews, SignUpViews, UpdateTokenVerifyView, UpdateTokenRefreshView,ChangePasswordView, PasswordResetRequestView, PasswordResetConfirmView, UserSignUpOTPVerifyView
from rest_framework.routers import DefaultRouter
from .site_views import SignUpSliderViewset, CustomerScreenSlideViewset

router = DefaultRouter()
router.register(r"address", UserAddressViews, basename="user_address")

site_router = DefaultRouter()
site_router.register(r"signup-slide", SignUpSliderViewset, basename="site-signup-slide")
site_router.register(r"customer-screen", CustomerScreenSlideViewset, basename="customer-screen")


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
    path("signup/otp/request/", SignUpOTPRequestView.as_view(), name="signup_otp_send"),
    path("signup/otp/verify/", SignUpOTPVerifyView.as_view(), name="signup_otp_verify"),
    path("auth/signup/", SignUpViews.as_view(), name="signup"),
    path("auth/signup/verify/", UserSignUpOTPVerifyView.as_view(), name="signup-verify"),
    

    # path('auth/', include('social_django.urls', namespace='social')),
    # path('auth/complete/google-oauth2/<str:backend>{extra}', social_auth_redirect, name="social_auth_redirect"),
    # path('auth/complete/google-oauth2/<str:backend>{extra}', SocialLoginCompleteView.as_view(), name="social_auth_redirect"),
    # path("auth/social/success/", SocialAuthSuccessView.as_view(), name="social_auth_success"),


    
    path("current-user/", UserInfoView.as_view(), name="current_user_info"),
    path("user/", include(router.urls)),




    # Site Settings Urls========================================
    path("site/", include(site_router.urls)),
]