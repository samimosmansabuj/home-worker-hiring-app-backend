import json
import math
import math
from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import OTP, User, Address, CustomerProfile, ServiceProviderProfile, CustomerPaymentMethod, ProviderPayoutMethod, UserLanguage, Referral, Voucher
from .serializers import (
    LoginOTPRequestSerializer, LoginOTPVerifySerializer, ProviderSerializer, SignUpOTPRequestSerializer, SignUpOTPVerifySerializer, UserInfoSerializer, UserAddressSerializer, SignupSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, CustomTokenObtainPairSerializer, ProviderVerificationSerializer, CustomerPaymentMethodSerializer, ProviderPayoutMethodSerializer, ReferralSerializer, VoucherSerializer, ApplyVoucherSerializer
)
from core.models import AddOfferVoucher
from .utils import generate_otp, KYCVerificationService
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt
from find_worker_config.permissions import IsCustomer, IsValidFrontendRequest
from find_worker_config.model_choice import OTPType, UserRole, UserDefault, DocumentStatus, UserStatus, VOUCHER_DISCOUNT_TYPE, VOUCHER_TYPE
from .models import User, OTP, ProviderVerification
from .utils import generate_otp, get_otp_object
from find_worker_config.utils import UpdateModelViewSet, UpdateReadOnlyModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from find_worker_config.utils import LogActivityModule
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from rest_framework.decorators import action
User = get_user_model()
import requests
import os



class WelComeAPI(APIView):
    # permission_classes = [permissions.AllowAny, IsValidFrontendRequest]
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Welcome to API Started!!!"
            }, status=status.HTTP_200_OK
        )

class PasswordLoginViews(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    def create_log(self, user, action, entity, metadata={}):
        # user, action, entity, metadata, request
        data = {
            "user": user,
            "action": action,
            "entity": entity,
            "request": self.request,
            "metadata": {"login_method": "password"}
        }
        log = LogActivityModule(data)
        log.create()

    def post(self, request: Request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.get_user()
            self.create_log(user, "New Login", user)
            data = serializer.validated_data
            data["default_profile"] = user.default_profile
            return Response(
                {
                    "status": True,
                    "data": data
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

# Login With OTP Start===========================
class LoginOTPRequestView(APIView):
    def post(self, request):
        try:
            serializer = LoginOTPRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(
                {
                    "status": True,
                    "message": "OTP sent",
                    "data": serializer.create_otp_object()
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class LoginOTPVerifyView(APIView):
    def get_otp_object(self, data):
        otp = data.get("otp")
        email = data.get("email")
        phone = data.get("phone")

        query = Q(code=otp, is_used=False, purpose=OTPType.LOGIN)
        if phone:
            query &= Q(phone=phone)
        if email:
            query &= Q(email=email)
        otp_object = OTP.objects.filter(query).last()

        if not otp_object:
            raise Exception("Invalid OTP")

        if otp_object.is_expired():
            raise Exception("OTP expired")

        otp_object.is_used = True
        otp_object.save(update_fields=["is_used"])
        return otp_object

    def create_log(self, user, action, entity, metadata={}):
        data = {
            "user": user,
            "action": action,
            "entity": entity,
            "request": self.request,
            "metadata": {"login_method": "OTP Login"}
        }
        log = LogActivityModule(data)
        log.create()
    
    def post(self, request):
        try:
            with transaction.atomic():
                serializer = LoginOTPVerifySerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                otp = self.get_otp_object(serializer.validated_data)
                self.create_log(otp.user, "New Login", otp.user)
                return Response(
                    {
                        "status": True,
                        "data": serializer.authenticated(otp.user)
                    }, status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
# Login With OTP End===========================

# SignUp With OTP Start===========================
class SignUpOTPRequestView(APIView):
    def get_otp_object(self, data):
        otp = generate_otp(6)
        email = data.get("email", None)
        phone = data.get("phone", None)
        if email and User.objects.filter(email=email).exists():
            raise Exception("Email Already Taken!")
        if phone and User.objects.filter(phone=phone).exists():
            raise Exception("Phone Already Taken!")
        otp_obj = OTP.objects.create(
            phone=phone,
            email=email,
            code=otp,
            purpose=OTPType.SIGNUP
        )
        return otp_obj

    def get_response(self, otp_object: OTP):
        if otp_object.phone is not None:
            return {"phone": otp_object.phone}
        elif otp_object.email is not None:
            return {"email": otp_object.email}

    def post(self, request):
        try:
            serializer = SignUpOTPRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            otp_object = self.get_otp_object(serializer.validated_data)
            return Response(
                {
                    "status": True,
                    "message": "OTP sent",
                    "data": self.get_response(otp_object)
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class SignUpOTPVerifyView(APIView):
    def get_otp_object(self, data):
        otp = data.get("otp")
        email = data.get("email")
        phone = data.get("phone")

        query = Q(code=otp, is_used=False, purpose=OTPType.SIGNUP)
        if phone:
            query &= Q(phone=phone)
        if email:
            query &= Q(email=email)
        otp_object = OTP.objects.filter(query).last()

        if not otp_object:
            raise Exception("Invalid OTP")

        if otp_object.is_expired():
            raise Exception("OTP expired")

        otp_object.is_used = True
        otp_object.save(update_fields=["is_used"])
        return otp_object
    
    def get_and_create_user(self, otp_object: OTP):
        if otp_object.phone:
            user, created = User.objects.get_or_create(
                phone=otp_object.phone, role=UserRole.USER, is_phone_verified=True
            )
        elif otp_object.email:
            user, created = User.objects.get_or_create(
                email=otp_object.email, role=UserRole.USER, is_email_verified=True
            )
        else:
            raise Exception("User not created, somethings wrong!")
        otp_object.user = user
        otp_object.save(update_fields=["user"])
        return user

    def post(self, request):
        try:
            serializer = SignUpOTPVerifySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            otp_obj = self.get_otp_object(serializer.validated_data)
            user = self.get_and_create_user(otp_obj)
            return Response(
                {
                    "status": True,
                    "data": serializer.authenticated(user)
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
# -------------------------------------------------
class SignUpViews(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = SignupSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            email = serializer.send_code()
            return Response(
                {
                    "status": True,
                    "message": "OTP send to your email address.",
                    "data": email
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                },status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserSignUpOTPVerifyView(APIView):
    def create_log(self, user, action, entity, metadata={}):
        data = {
            "user": user,
            "action": action,
            "entity": entity,
            "request": self.request,
            "metadata": {"login_method": "User Registration & Verify"}
        }
        log = LogActivityModule(data)
        log.create()
    
    def post(self, request):
        try:
            with transaction.atomic():
                serializer = SignUpOTPVerifySerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                otp_obj = get_otp_object(serializer.validated_data, OTPType.SIGNUP)
                user = otp_obj.user
                if not user:
                    raise Exception("Not get user using this OTP.")
                user.is_email_verified=True
                user.save()
                self.create_log(user, "New Registration & Verify", user)
            return Response(
                {
                    "status": True,
                    "data": serializer.authenticated(user)
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

# SignUp With OTP End===========================




# =================================================================
# Social Auth Login System Views Start---------------
class GoogleLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def google_response(self, access_token: str) -> dict:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            # "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5
        )
        if response.status_code != 200:
            raise Exception("Invalid Google token")
        google_data = response.json()
        return google_data
    
    def save_google_profile_photo(self, user: object, picture_url: str) -> bool:
        response = requests.get(picture_url, timeout=10)
        if response.status_code != 200:
            return
        filename = f"user_{user.id}_google.jpg"
        user.photo.save(filename, ContentFile(response.content), save=True)
        return True

    def get_user(self, google_data: dict) -> object:
        email = google_data.get("email")
        first_name = google_data.get("given_name", "")
        last_name = google_data.get("family_name", "")
        picture = google_data.get("picture", "")

        if not email:
            raise Exception("Email not available.")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name
            }
        )

        if created and not user.phone and picture:
            self.save_google_profile_photo(user, picture)

        return user

    def post(self, request):
        try:
            with transaction.atomic():
                access_token = request.data.get('access_token')

                if not access_token:
                    raise Exception("access_token is required")
                
                google_data = self.google_response(access_token)

                user = self.get_user(google_data)
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "status": True,
                        "data": {
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                            "default_profile": user.default_profile
                        }
                    }, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }
            )

class AppleLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def google_response(self, access_token: str) -> dict:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            # "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5
        )
        if response.status_code != 200:
            raise Exception("Invalid Google token")
        google_data = response.json()

        # if data.get("aud") != settings.GOOGLE_CLIENT_ID:
        #     raise Exception("Token audience mismatch")

        return google_data
    
    def save_google_profile_photo(self, user: object, picture_url: str) -> bool:
        response = requests.get(picture_url, timeout=10)
        if response.status_code != 200:
            return
        filename = f"user_{user.id}_google.jpg"
        user.photo.save(filename, ContentFile(response.content), save=True)
        return True

    def get_user(self, google_data: dict) -> object:
        email = google_data.get("email")
        first_name = google_data.get("given_name", "")
        last_name = google_data.get("family_name", "")
        picture = google_data.get("picture", "")

        if not email:
            raise Exception("Email not available.")

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name
            }
        )

        if created and not user.phone and picture:
            self.save_google_profile_photo(user, picture)

        return user

    def post(self, request):
        try:
            with transaction.atomic():
                access_token = request.data.get('access_token')

                if not access_token:
                    raise Exception("access_token is required")
                
                google_data = self.google_response(access_token)

                user = self.get_user(google_data)
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "status": True,
                        "data": {
                            "access": str(refresh.access_token),
                            "refresh": str(refresh),
                        }
                    }, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }
            )


# Social Auth Login System Views END---------------
# =================================================================



# Token & Password Start=================================
class UpdateTokenVerifyView(TokenVerifyView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(
                {
                    "status": False,
                    "message": "Token Valid!"
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class UpdateTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args, **kwargs) -> Response:
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            return Response(
                {
                    "status": True,
                    "data": serializer.validated_data
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def create_log(self):
        data = {
            "user": self.request.user,
            "action": "Password Change",
            "entity": self.request.user,
            "request": self.request,
            "metadata": {},
            "for_notify": True
        }
        log = LogActivityModule(data)
        log.create()
    
    def post(self, request):
        try:
            with transaction.atomic():
                serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
                serializer.is_valid(raise_exception=True)
                serializer.set_password()
                self.create_log()
                return Response(
                    {
                        "status": True,
                        "message": "Password changed successfully"
                    },
                    status=status.HTTP_200_OK
                )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetRequestView(APIView):
    def post(self, request):
        try:
            serializer = PasswordResetRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            send_to = serializer.send_code()
            return Response(
                {
                    "status": True,
                    "message": "OTP send for reset your password.",
                    "send_to": send_to
                },
                status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetConfirmView(APIView):
    def post(self, request):
        try:
            serializer = PasswordResetConfirmSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            otp = get_otp_object(serializer.validated_data, OTPType.RESET_PASSWORD)
            serializer.set_new_password(otp.user)
            return Response(
                {
                    "status": True,
                    "message": "Password Reset Sucessfully.",
                },
                status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Token & Password End=================================



# User Info Current ===========================
class UserInfoView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserInfoSerializer

    def create_log(self):
        data = {
            "user": self.request.user,
            "action": "Profile Update",
            "entity": self.request.user,
            "request": self.request,
            "metadata": {}
        }
        log = LogActivityModule(data)
        log.create()

    def get_object(self):
        user = self.request.user
        return user
    
    def get_user_mode_profile(self, user_mode):
        user = self.get_object()
        if user_mode == UserDefault.CUSTOMER:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            if not ServiceProviderProfile.objects.filter(user=user).exists() and not user.default_profile:
                user.default_profile = UserDefault.CUSTOMER
        elif user_mode == UserDefault.PROVIDER:
            profile, _ = ServiceProviderProfile.objects.get_or_create(user=user)
            if not CustomerProfile.objects.filter(user=user).exists() and not user.default_profile:
                user.default_profile = UserDefault.PROVIDER
        else:
            return None
        user.save(update_fields=["default_profile"])
        return profile
    
    def retrieve(self, request, *args, **kwargs):
        user_mode = request.query_params.get("user_mode")
        self.get_user_mode_profile(user_mode)
        instance = self.get_object()
        return Response(
            {
                'status': True,
                'data': self.get_serializer(instance, context={"user_mode": user_mode, "request": request}).data
            }, status=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        user_mode = request.query_params.get("user_mode")
        try:
            with transaction.atomic():
                self.get_user_mode_profile(user_mode)
                partial = kwargs.pop('partial', False)
                instance = self.get_object()
                serializer = UserInfoSerializer(
                    instance, data=request.data, partial=partial, context={
                        "user_mode": user_mode, "request": request
                    }
                )
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

                if getattr(instance, '_prefetched_objects_cache', None):
                    instance._prefetched_objects_cache = {}
                
                self.create_log()
                return Response(
                    {
                        "status": True,
                        "data": serializer.data
                    }
                )
        except ValidationError as e:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )

class UserAddressViews(UpdateModelViewSet):
    model = Address
    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_user(self):
        return self.request.user

    def get_queryset(self):
        user = self.get_user()
        if self.request.user.role == UserRole.USER:
            return Address.objects.filter(user=user)
        elif self.request.user.role in (UserRole.ADMIN):
            return Address.objects.all()
        raise Exception("Wrong user!")
    
    def list(self, request, *args, **kwargs):
        try:
            response = UserAddressSerializer(self.get_queryset(), many=True)
            return Response(
                {
                    'status': True,
                    'count': len(response.data),
                    'data': response.data
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'messgae': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_log(self, entity, action):
        data = {
            "user": self.request.user,
            "action": action,
            "entity": entity,
            "request": self.request,
            "metadata": {}
        }
        log = LogActivityModule(data)
        log.create()

    def perform_create(self, serializer):
        address_serializer = serializer.save(is_default=True)
        self.create_log(address_serializer, "Add new address")
        return address_serializer
    
    def perform_update(self, serializer):
        address_serializer = serializer.save(is_default=True)
        self.create_log(address_serializer, "Update address")
        return address_serializer

    def perform_retrieve(self, serializer):
        instance = self.get_object()
        instance.is_default = True
        instance.save(update_fields=["is_default"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                'status': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK
        )

class ProviderVerificationViews(APIView):
    serializer_class = ProviderVerificationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            if request.user.role == UserRole.USER:
                serializer = self.serializer_class(request.user.service_provider_profile.verification, context={"request": request})
            elif request.user.role == UserRole.ADMIN:
                serializer = self.serializer_class(ProviderVerification.objects.all(), many=True, context={"request": request})
            else:
                raise Exception("Wrong user.")
            
            return Response(
                {
                    "status": True,
                    "data": serializer.data
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }
            )
    
    def post(self, request):
        try:
            if not self.request.user.hasServiceProviderProfile:
                raise Exception("This user have no provider profile.")
                        
            provider = request.user.hasServiceProviderProfile
            verification = provider.verification
            if request.user.status == UserStatus.ACTIVE and provider.is_verified and verification.is_verified:
                raise Exception(_("Already Verified!"))

            serializer = self.serializer_class(verification, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            image_path = verification.document.path

            service = KYCVerificationService(image_path, request.user)
            result = service.verify()

            provider.is_verified = result.get('verified', False)
            provider.save(update_fields=["is_verified"])
            verification.is_verified = result.get('verified', False)
            verification.status == DocumentStatus.APPROVED if result.get('verified', False) else result.get("status", DocumentStatus.FAILED)
            verification.save(update_fields=["is_verified", "status"])            
            return Response(
                {
                    "status": True,
                    "kyc_result": result
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserDefaultLanguage(APIView):
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

class ProviderAddressUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if not self.request.user.hasServiceProviderProfile:
                raise Exception("This user have no provider profile.")
            provider = request.user.hasServiceProviderProfile
            data = request.data
            address_object_id = data.get("address_object_id", None)
            if address_object_id is None:
                raise Exception("Address object id is required.")
            address = get_object_or_404(
                Address, id=address_object_id, user=request.user
            )
            if not address:
                raise Exception("Address not found with this id for this user.")
            provider.office_location = address
            provider.save(update_fields=["office_location"])
            return Response(
                {
                    "status": True,
                    "message": "Office location updated successfully."
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# User Info Current ===========================


# Referral & Voucher Views==================================
# -------------------------------
# My Referral Views
class MyReferralViewSet(UpdateReadOnlyModelViewSet):
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user) 
# -------------------------------
# -------------------------------
# Voucher Views
class MyVoucherViewSet(UpdateReadOnlyModelViewSet):
    serializer_class = VoucherSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        vouchers = Voucher.objects.filter(
            Q(user=self.request.user, voucher_type=VOUCHER_TYPE.FOR_USER) | Q(voucher_type=VOUCHER_TYPE.FOR_GLOBAL)
        )
        return vouchers

    @action(detail=False, methods=["post"], url_path="add-voucher")
    def add_voucher(self, request):
        try:
            voucher_code = request.data.get("voucher_code")
            if not voucher_code:
                raise Exception("Voucher code field is empty!")
            elif self.get_queryset().filter(code=voucher_code).exists():
                raise Exception("You've already saved this one! Find in Vouchers")
            elif not AddOfferVoucher.objects.filter(code=voucher_code).exists():
                raise Exception("This voucher does not exist. Please check if the voucher code was keyed in correctly.")
            
            with transaction.atomic():
                offer_voucher = AddOfferVoucher.objects.get(code=voucher_code)
                Voucher.objects.create(
                    user=self.request.user,
                    voucher_type=VOUCHER_TYPE.FOR_USER,
                    name=offer_voucher.name,
                    code=offer_voucher.code,
                    discount_type=offer_voucher.discount_type,
                    value=offer_voucher.value,
                    minimum_value=offer_voucher.minimum_value,
                    upto_value=offer_voucher.upto_value,
                    expiry_date=offer_voucher.expiry_date,
                )
                return Response(
                    {
                        "status": True,
                        "message": f"{voucher_code} Add in your account. Find in Vouchers."
                    }
                )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
# -------------------------------
# -------------------------------
# Apply Voucher (Important)
class ApplyVoucherView(APIView):
    serializer_class = ApplyVoucherSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)

            voucher = serializer.validated_data["voucher"]
            amount = serializer.validated_data["order_amount"]

            # Calculate discount
            if voucher.discount_type == VOUCHER_DISCOUNT_TYPE.PERCENTAGE:
                discount = (voucher.value / 100) * amount
            else:
                discount = voucher.value

            if voucher.upto_value:
                discount = min(discount, voucher.upto_value)

            final_amount = amount - discount

            return Response({
                "voucher_id": voucher.id,
                "voucher_code": voucher.code,
                "original_amount": amount,
                "discount": discount,
                "final_amount": final_amount
            }, status=status.HTTP_200_OK)
        except ValidationError:
            errors = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": errors
                }
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }
            )
# -------------------------------
# Referral & Voucher Views==================================


# Buyer/Helper List for Customer/Client===================
class HelperListViewset(UpdateReadOnlyModelViewSet):
    queryset = User.objects.filter(
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        service_provider_profile__isnull=False
    ).select_related("service_provider_profile")
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return {
            "request": self.request
        }
    
    def haversine(self, lat1, lon1, lat2, lon2):
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return round(6371 * c, 2)
    
    def get_map_distance(self, lat1, lon1, lat2, lon2):
        api_key = os.getenv("GOOGLE_MAP_API_KEY")
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": f"{lat1},{lon1}",
            "destinations": f"{lat2},{lon2}",
            "key": api_key
        }
        response = requests.get(url, params=params)
        print("Google Maps API Response:", response.text)  # Debug log
        if response.status_code != 200:
            return None
        data = response.json()
        try:
            distance_text = data["rows"][0]["elements"][0]["distance"]["text"]
            distance_value = float(distance_text.replace(" km", "").replace(",", ""))
            return distance_value
        except (KeyError, IndexError, ValueError):
            return None

    def get_queryset(self):
        user = self.request.user
        address = Address.objects.filter(user=user, is_default=True).first()
        if not address:
            return User.objects.none()
        user_lat = address.lat
        user_lng = address.lng

        queryset = User.objects.filter(
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            service_provider_profile__isnull=False
        ).exclude(
            id=user.id
        ).select_related(
            "service_provider_profile__office_location"
        ).prefetch_related(
            "service_provider_profile__service_category"
        )

        # ---- Query Params ----
        category_id = self.request.query_params.get("category_id")
        subcategory_id = self.request.query_params.get("subcategory_id")
        min_rating = self.request.query_params.get("rating")
        radius = self.request.query_params.get("radius")

        # ---- Category Filter ----
        if subcategory_id:
            queryset = queryset.filter(
                service_provider_profile__service_subcategory__id=subcategory_id
            )
        elif category_id:
            queryset = queryset.filter(
                service_provider_profile__service_category__id=category_id
            )

        # ---- Rating Filter ----
        if min_rating:
            queryset = queryset.filter(
                service_provider_profile__rating__gte=float(min_rating)
            )

        # ---- Distance Calculation (ALWAYS attach) ----
        providers_with_distance = []
        for provider in queryset:
            office = provider.service_provider_profile.office_location
            if not office or not office.lat or not office.lng:
                continue
            distance = self.haversine(
                user_lat,
                user_lng,
                office.lat,
                office.lng
            )
            provider.distance_km = distance

            # ---- Radius Filter ----
            if radius:
                if distance <= float(radius):
                    providers_with_distance.append(provider)
            else:
                providers_with_distance.append(provider)

        providers_with_distance.sort(key=lambda x: x.distance_km)
        return providers_with_distance

# Buyer/Helper List for Customer/Client===================



# =================================================================
# Payment & Payout method Viewsets ===========================
class CustomerPaymentMethodViewSet(UpdateModelViewSet):
    serializer_class = CustomerPaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomerPaymentMethod.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        obj = self.get_object()
        CustomerPaymentMethod.objects.filter(
            user=request.user
        ).update(is_default=False)
        obj.is_default = True
        obj.save()
        return Response({"status": True, "message": "Default updated"}, status=status.HTTP_200_OK)

class ProviderPayoutMethodViewSet(UpdateModelViewSet):
    serializer_class = ProviderPayoutMethodSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProviderPayoutMethod.objects.filter(
            provider=self.request.user.hasServiceProviderProfile
        )

    def perform_create(self, serializer):
        serializer.save(
            provider=self.request.user.hasServiceProviderProfile
        )

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        obj = self.get_object()
        self.get_queryset().update(is_default=False)
        obj.is_default = True
        obj.save()
        return Response({"status": True, "message": "Default updated"}, status=status.HTTP_200_OK)

# Payment & Payout method Viewsets ===========================
# =================================================================



