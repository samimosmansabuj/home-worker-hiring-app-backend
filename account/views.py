from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import status, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import OTP, User, Address, CustomerProfile, ServiceProviderProfile
from .serializers import LoginOTPRequestSerializer, LoginOTPVerifySerializer, SignUpOTPRequestSerializer, SignUpOTPVerifySerializer, UserInfoSerializer, UserAddressSerializer, SignupSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, CustomTokenObtainPairSerializer, ProviderVerificationSerializer
from .utils import generate_otp, KYCVerificationService
from django.db.models import Q
from find_worker_config.permissions import IsCustomer, IsValidFrontendRequest
from find_worker_config.model_choice import OTPType, UserRole, UserDefault, DocumentStatus, UserStatus
from .models import User, OTP, ProviderVerification
from .utils import generate_otp, get_otp_object
from find_worker_config.utils import UpdateModelViewSet
from django.contrib.contenttypes.models import ContentType
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from find_worker_config.utils import LogActivityModule
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from urllib.parse import urlparse
from django.core.files.base import ContentFile
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
            return Response(
                {
                    "status": True,
                    "data": serializer.validated_data
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
            if not ServiceProviderProfile.objects.filter(user=user).exists() and not user.default_user:
                user.default_user = UserDefault.CUSTOMER
            return profile
        elif user_mode == UserDefault.PROVIDER:
            profile, _ = ServiceProviderProfile.objects.get_or_create(user=user)
            if not CustomerProfile.objects.filter(user=user).exists() and not user.default_user:
                user.default_user = UserDefault.PROVIDER
            return profile
        else:
            return None
    
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
                serializer = UserInfoSerializer(instance, data=request.data, partial=partial, context={"user_mode": user_mode, "request": request})
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

    def get_user_mode_profile(self, user_mode):
        user = self.get_user()
        if user_mode == UserDefault.CUSTOMER:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            return profile
        elif user_mode == UserDefault.PROVIDER:
            profile, _ = ServiceProviderProfile.objects.get_or_create(user=user)
            return profile
        else:
            return None

    def get_queryset(self):
        if self.request.user.role == UserRole.USER:
            return Address.objects.filter(user=self.request.user)
        elif self.request.user.role in (UserRole.ADMIN):
            return Address.objects.all()
        raise Exception("Wrong user!")

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
        user_mode = self.request.query_params.get("user_mode")
        profile = self.get_user_mode_profile(user_mode)
        address_serializer = serializer.save(profile_type=ContentType.objects.get_for_model(profile), object_id=profile.id)
        self.create_log(address_serializer, "Add new address")
        return address_serializer

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
        
# User Info Current ===========================



