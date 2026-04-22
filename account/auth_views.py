from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView, TokenRefreshView
from .serializers import (
    LoginOTPRequestSerializer, LoginOTPVerifySerializer, SignUpOTPRequestSerializer, SignUpOTPVerifySerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, SignupSerializer, CustomTokenObtainPairSerializer
)
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import OTP
from find_worker_config.model_choice import OTPType, UserRole, LogStatus
from django.core.files.base import ContentFile
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from find_worker_config.utils import LogActivityModule
from .utils import  get_otp_object
from django.shortcuts import get_object_or_404
from account.models import User



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

# Login With OTP End============================


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
    def create_log(self, user):
        data = {
            "user": user,
            "action": "New Registration",
            "entity": user,
            "request": self.request,
            "metadata": {"registration_method": "User Registration & Verify"}
        }
        log = LogActivityModule(data)
        log.create()
    
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                serializer = SignupSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                user = serializer.save()
                email = serializer.send_code()
                self.create_log(user)
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
    def create_log(self, user, log_status):
        data = {
            "user": user,
            "action": "Account Verification",
            "status": log_status,
            "entity": user,
            "request": self.request,
            "metadata": {"account_verify": "User Registration & Verify"}
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
                self.create_log(user, LogStatus.SUCCESS)
            return Response(
                {
                    "status": True,
                    "data": serializer.authenticated(user)
                }, status=status.HTTP_200_OK
            )
        except ValidationError:
            # self.create_log(self.request.user, LogStatus.FAILED)
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    "status": False,
                    "message": error
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # self.create_log(self.request.user, LogStatus.FAILED)
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class SignUpOTPResend(APIView):
    def create_log(self, user, log_status):
        data = {
            "user": user,
            "action": "Verification OTP Resend",
            "status": log_status,
            "entity": user,
            "request": self.request,
            "metadata": {"verification_otp_resend": "User Registration & Verify"}
        }
        log = LogActivityModule(data)
        log.create()
    
    def get_user_by_email(self, email):
        return get_object_or_404(User, email=email)

    def send_code(self, email):
        user = self.get_user_by_email(email)
        if not user:
            raise Exception("User can't found with this email.")
        otp = OTP.objects.create(
            user=user,
            email=email,
            purpose=OTPType.SIGNUP
        )
        return otp.email
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            email = data.get("email", None)
            if not email:
                raise Exception("Need email for resend email!")
            self.send_code(email)
            self.create_log(self.get_user_by_email(email), LogStatus.SUCCESS)
            return Response(
                {
                    "status": True,
                    "message": "OTP Resend!"
                }, status=status.HTTP_200_OK
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
