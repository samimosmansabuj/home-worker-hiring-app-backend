from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import status, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.request import Request
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import OTP, User, Address, CustomerProfile, ServiceProviderProfile
from .serializers import LoginOTPRequestSerializer, LoginOTPVerifySerializer, SignUpOTPRequestSerializer, SignUpOTPVerifySerializer, UserInfoSerializer, UserAddressSerializer, SignupSerializer
from .utils import generate_otp
from django.db.models import Q
from find_worker_config.permissions import IsCustomer, IsValidFrontendRequest
from find_worker_config.model_choice import OTPType, UserRole, UserDefault
from .models import User, OTP
from .utils import generate_otp
from find_worker_config.utils import UpdateModelViewSet
from django.contrib.contenttypes.models import ContentType
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated


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
    def post(self, request: Request, *args, **kwargs):
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

    def post(self, request):
        try:
            serializer = LoginOTPVerifySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            otp = self.get_otp_object(serializer.validated_data)
            # refresh = RefreshToken.for_user(user)

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
                phone=otp_object.phone, role=UserRole.USER
            )
        elif otp_object.email:
            user, created = User.objects.get_or_create(
                email=otp_object.email, role=UserRole.USER
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

class SignUpViews(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = SignupSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "data": serializer.authenticated(serializer.instance)
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

# class SocialLoginCompleteView(APIView):
#     # permission_classes = []
#     def post(self, request, backend, *args, **kwargs):
#         user = request.user
#         refresh = RefreshToken.for_user(user)
#         print("refresh: ", refresh)
#         print("backend: ", backend)

#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": {
#                 "id": user.id,
#                 "email": user.email,
#                 "username": user.username,
#             }
#         })
    
#     def get(self, request, backend, *args, **kwargs):
#         user = request.user
#         refresh = RefreshToken.for_user(user)
#         print("refresh: ", refresh)
#         print("backend: ", backend)

#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": {
#                 "id": user.id,
#                 "email": user.email,
#                 "username": user.username,
#             }
#         })

# class SocialAuthSuccessView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user
#         refresh = RefreshToken.for_user(user)

#         return Response({
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#             "user": {
#                 "id": user.id,
#                 "email": user.email,
#                 "username": user.username,
#             }
#         })

# def social_auth_redirect(request, backend, *args, **kwargs):
#     return HttpResponse("Success")

# SignUp With OTP End===========================


# User Info Current ===========================
class UserInfoView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserInfoSerializer

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
                'data': self.get_serializer(instance, context={"user_mode": user_mode}).data
            }, status=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        user_mode = request.query_params.get("user_mode")
        try:
            self.get_user_mode_profile(user_mode)
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = UserInfoSerializer(instance, data=request.data, partial=partial, context={"user_mode": user_mode})
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            return Response(serializer.data)
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

    def perform_create(self, serializer):
        user_mode = self.request.query_params.get("user_mode")
        profile = self.get_user_mode_profile(user_mode)
        return serializer.save(profile_type=ContentType.objects.get_for_model(profile), object_id=profile.id)

# User Info Current ===========================

