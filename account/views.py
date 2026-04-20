from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView, CreateAPIView, GenericAPIView
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError

from job.serializers import ProviderSerializer
from .models import Address, CustomerProfile, HelperWeeklyAvailability, ServiceProviderProfile, CustomerPaymentMethod, ProviderPayoutMethod, UserLanguage, Referral, Voucher, SavedHelper
from .serializers import (
    HelperWeeklyAvailabilitySerializer, ReviewAndRatingProfileSerializer, UserAddressSerializer, ProviderVerificationSerializer, CustomerPaymentMethodSerializer, ProviderPayoutMethodSerializer, ReferralSerializer, VoucherSerializer, ApplyVoucherSerializer, CurrentUserInfoSerializer, CurrentUserHelperSerializer, SaveHelperProfileSerializer
)
from core.models import AddOfferVoucher
# from .utils import generate_otp, KYCVerificationService
from django.db.models import F, Q, Avg, ExpressionWrapper, FloatField, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.viewsets import GenericViewSet
from find_worker_config.model_choice import OrderStatus, UserRole, UserDefault, DocumentStatus, UserStatus, VOUCHER_DISCOUNT_TYPE, VOUCHER_TYPE
from .models import ProviderVerification
from .utils import generate_otp, get_otp_object
from find_worker_config.utils import UpdateModelViewSet, UpdateReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from find_worker_config.utils import LogActivityModule
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


from rest_framework.decorators import action
User = get_user_model()




class WelComeAPI(APIView):
    # permission_classes = [permissions.AllowAny, IsValidFrontendRequest]
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "APi Active!!!"
            }, status=status.HTTP_200_OK
        )


# User Info Current ===========================
class CurrentUserInfoView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserInfoSerializer

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
            profile = get_object_or_404(ServiceProviderProfile, user=user)
            if not profile:
                raise Exception("Helper Profile Not Created!")
            if not CustomerProfile.objects.filter(user=user).exists() and not user.default_profile:
                user.default_profile = UserDefault.PROVIDER
        else:
            return None
        user.save(update_fields=["default_profile"])
        return profile
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
    
    def retrieve(self, request, *args, **kwargs):
        user_mode = request.query_params.get("user_mode")
        self.get_user_mode_profile(user_mode)
        instance = self.get_object()
        return Response(
            {
                'status': True,
                'data': self.get_serializer(instance).data
            }, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                partial = kwargs.pop('partial', False)
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
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

class CurrentUserHelperView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserHelperSerializer

    def create_log(self):
        data = {
            "user": self.request.user,
            "action": "Helper Profile Update",
            "entity": self.request.user.service_provider_profile,
            "request": self.request,
            "metadata": {}
        }
        log = LogActivityModule(data)
        log.create()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
    
    def get_object(self):
        user = self.request.user
        try:
            return ServiceProviderProfile.objects.get(user=user)
        except ServiceProviderProfile.DoesNotExist:
            raise NotFound(detail="Helper Profile Not Created")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {
                'status': True,
                'data': self.get_serializer(instance).data
            }, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                partial = kwargs.pop('partial', False)
                instance = self.get_object()
                serializer = self.get_serializer(instance, data=request.data, partial=partial)
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

class CreateUserHelperView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CurrentUserHelperSerializer

    def create_log(self):
        data = {
            "user": self.request.user,
            "action": "Helper Profile Created",
            "entity": self.request.user.service_provider_profile,
            "request": self.request,
            "metadata": {}
        }
        log = LogActivityModule(data)
        log.create()

    def get_object(self):
        user = self.request.user
        if self.get_helper_profile(user):
            raise Exception("Helper profile already created!")
        return user
    
    def get_helper_profile(self, user):
        if ServiceProviderProfile.objects.filter(user=user).exists():
            return True
        return False

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save(user=self.get_object())
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
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class UserAddressViews(UpdateModelViewSet):
    model = Address
    queryset = Address.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

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

            # service = KYCVerificationService(image_path, request.user)
            # result = service.verify()
            result = True

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

class ReviewAndRatingProfileViewSet(GenericViewSet):
    serializer_class = ReviewAndRatingProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["profile_type"] = self.request.headers.get("profile_type", "").upper()
        return context
    
    @action(detail=False, methods=["get"], url_path="customer(?:/(?P<review_id>[^/.]+))?")
    def customer_reviews(self, request, review_id=None):
        if review_id:
            review = get_object_or_404(
                ReviewAndRating,
                id=review_id,
                customer=request.user.customer_profile,
                send_by=UserDefault.PROVIDER
            )
            serializer = self.get_serializer(review)
        else:
            reviews = ReviewAndRating.objects.filter(
                customer=request.user.customer_profile,
                send_by=UserDefault.PROVIDER
            )
            serializer = self.get_serializer(reviews, many=True)

        return Response({
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="provider(?:/(?P<review_id>[^/.]+))?")
    def provider_reviews(self, request, review_id=None):
        if review_id:
            review = get_object_or_404(
                ReviewAndRating,
                id=review_id,
                provider=request.user.hasServiceProviderProfile,
                send_by=UserDefault.CUSTOMER
            )
            serializer = self.get_serializer(review)
        else:
            reviews = ReviewAndRating.objects.filter(
                provider=request.user.hasServiceProviderProfile, send_by=UserDefault.CUSTOMER
            )
            serializer = self.get_serializer(reviews, many=True)
        return Response(
            {
                "status": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK
        )

# User Info Current ===========================


# ===============================================================================
# Helper/Provider User Related API Views Start================================
class HelperWeeklyAvailabilityViewSet(UpdateModelViewSet):
    serializer_class = HelperWeeklyAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HelperWeeklyAvailability.objects.filter(provider=self.request.user.service_provider_profile)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "status": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK
        )
    

# Helper/Provider User Related API Views End==================================
# ===============================================================================

# ===============================================================================
# Customer User Related API Views Start================================
from task.models import Order, ReviewAndRating
from .models import ActivityLog
class MyActivityViews(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        active_orders = Order.objects.filter(
            customer=self.request.user.customer_profile, status__in=[OrderStatus.ACCEPT, OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS]
        ).count()
        completed_orders = Order.objects.filter(
            customer=self.request.user.customer_profile, status__in=[OrderStatus.COMPLETED]
        ).count()
        total_spent = Order.objects.filter(
            customer=self.request.user.customer_profile, status__in=[OrderStatus.COMPLETED]
        ).aggregate(total=Sum('amount'))['total'] or 0
        avg_rating = ReviewAndRating.objects.filter(
            customer=self.request.user.customer_profile
        ).aggregate(avg=Avg('rating'))['avg'] or 0

        my_activity = {
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "total_spent": total_spent,
            "avg_rating": round(avg_rating, 2)
        }

        recent_activities = ActivityLog.objects.filter(
            user=self.request.user, user_type=UserDefault.CUSTOMER
        ).order_by('-created_at')[:5]
        recent_activity_data = [
            {
                "id": activity.id,
                "action": activity.action,
                "timestamp": activity.created_at
            }
            for activity in recent_activities
        ]
        return Response(
            {
                "status": True,
                "data": {
                    "my_activity": my_activity,
                    "recent_activities": recent_activity_data
                }
            }, status=status.HTTP_200_OK
        )

class SaveHelperProfileViews(UpdateReadOnlyModelViewSet):
    queryset = SavedHelper.objects.all()
    serializer_class = SaveHelperProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavedHelper.objects.filter(customer=self.request.user.customer_profile)
    
    @action(detail=False, methods=["post"], url_path="add-helper/(?P<helper_id>[^/.]+)")
    def add_helper(self, request, helper_id):
        try:
            if not ServiceProviderProfile.objects.filter(id=helper_id).exists():
                raise Exception("This helper does not exist. Please check if the helper id was keyed in correctly.")
            elif ServiceProviderProfile.objects.get(id=helper_id).user == request.user:
                raise Exception("You can't save your own profile!")
            elif self.get_queryset().filter(helper__id=helper_id).exists():
                raise Exception("You've already saved this one! Find in Saved Helpers")
            
            with transaction.atomic():
                helper_profile = ServiceProviderProfile.objects.get(id=helper_id)
                SavedHelper.objects.create(
                    customer=request.user.customer_profile,
                    helper=helper_profile
                )
                return Response(
                    {
                        "status": True,
                        "message": f"{helper_profile.user.first_name} {helper_profile.user.last_name} Add in your saved helpers. Find in Saved Helpers."
                    }, status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["delete"], url_path="remove-helper")
    def remove_helper(self, request, pk=None):
        try:
            saved_helper = self.get_object()
            saved_helper.delete()
            return Response(
                {
                    "status": True,
                    "message": "Helper removed from saved helpers."
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class GetMyReferralCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "status": True,
                "referral_code": self.request.user.referral_code or None
            }, status=status.HTTP_200_OK
        )

class RecommendationHelperViewSet(UpdateReadOnlyModelViewSet):
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_current_location_lat_lng(self):
        current_location = self.request.query_params.get("current_location", None)
        if current_location:
            try:
                lat, lng = map(float, current_location.split(","))
                return lat, lng
            except ValueError:
                return None
        else:
            current_location = self.request.user.addresses.filter(is_default=True).first()
            if current_location:
                return current_location.lat, current_location.lng
        return None
    
    def get_queryset(self):
        location = self.get_current_location_lat_lng() or (None, None)
        if location:
            user_lat, user_lng = location
            queryset = ServiceProviderProfile.objects.filter(is_verified=True)
            print("Queryset before annotation:", queryset)  # Debugging line to check the initial queryset
            distance_expr = ExpressionWrapper(
                ((Value(user_lat) - F('office_location__lat'))**2 +
                (Value(user_lng) - F('office_location__lng'))**2) ** 0.5,
                output_field=FloatField()
            )
            queryset = queryset.annotate(
                distance=distance_expr
            ).order_by('distance')[:3]
            return queryset[:3]

# Customer User Related API Views End==================================
# ===============================================================================



# Referral & Voucher Views==================================
# -------------------------------
# My Referral Views
class MyReferralViewSet(UpdateReadOnlyModelViewSet):
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Referral.objects.filter(referrer=self.request.user) 
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
# Apply Voucher (Important)
class ApplyVoucherView(GenericAPIView):
    serializer_class = ApplyVoucherSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
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



