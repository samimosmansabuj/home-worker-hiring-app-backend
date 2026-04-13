from django.shortcuts import render
from .serializers import ProviderSerializer
from account.models import Address, User, ServiceProviderProfile
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from find_worker_config.utils import UpdateReadOnlyModelViewSet, UpdateModelViewSet
from task.models import Order
from .serializers import OrderSerializerAll
from django.db import transaction
import requests
from rest_framework.exceptions import ValidationError, PermissionDenied
import os
from math import radians, cos, sin, asin, sqrt
from django.db.models import Q
from rest_framework.generics import CreateAPIView
from .paginations import HelperPagination

# ============================================================
# Buyer/Helper List for Customer/Client===================
class HelperListViewset(UpdateReadOnlyModelViewSet):
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HelperPagination

    def get_serializer_context(self):
        return {"request": self.request}
    
    def haversine(self, lat2, lon2):
        lon1, lat1, lon2, lat2 = map(
            radians, [self.user_lng, self.user_lat, lon2, lat2]
        )
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return round(6371 * c, 2)
    
    def get_map_distance(self,  lat2, lon2):
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

    def get_filter_data(self, queryset):
        # ---- Query Params ----
        q = self.request.query_params.get("q")
        category_id = self.request.query_params.get("category_id")
        distance_radius = self.request.query_params.get("distance_radius")
        budget = self.request.query_params.get("budget")
        min_rating = self.request.query_params.get("rating")
        availability = self.request.query_params.get("availability")

        # ---- Search Filter ----
        if q:
            queryset = queryset.filter(
                Q(company_name__icontains=q) |
                Q(details__icontains=q)
            )

        # ---- Category Filter ----
        if category_id:
            queryset = queryset.filter(
                service_category__id=category_id
            )

        # ---- Rating Filter ----
        if min_rating:
            queryset = queryset.filter(
                rating__gte=float(min_rating)
            )
        
        # ---- Availability ----
        if availability:
            queryset = queryset.filter(
                availability_status=availability
            )

        # ---- Budget ----
        if budget:
            queryset = queryset.filter(
                hourly_rate__lte=float(budget)
            )

        # ---- Distance Calculation (ALWAYS attach) ----
        helpers = []
        for helper in queryset:
            office = helper.office_location
            if not office or not office.lat or not office.lng:
                continue
            distance = self.haversine(office.lat, office.lng)
            # distance = self.get_map_distance(office.lat, office.lng)
            helper.distance_km = distance

            # ---- Distance Radius Filter ----
            if distance_radius:
                if distance <= float(distance_radius):
                    helpers.append(helper)
            else:
                helpers.append(helper)
        return helpers
    
    def get_queryset(self):
        user = self.request.user
        address = Address.objects.filter(user=user, is_default=True).first()
        if not address:
            return User.objects.none()
        self.user_lat = address.lat
        self.user_lng = address.lng

        return ServiceProviderProfile.objects.select_related(
            "user", "office_location"
        ).prefetch_related(
            "service_category"
        ).exclude(
            user=user
        )
    
    def get_sorting_queryset(self, queryset, sort_by):
        if sort_by == "rating":
            queryset.sort(key=lambda x: x.rating, reverse=True)
        elif sort_by == "price":
            queryset.sort(key=lambda x: x.hourly_rate or 0)
        elif sort_by == "distance" or not sort_by:
            queryset.sort(key=lambda x: x.distance_km)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        helpers = self.get_filter_data(queryset)
        sort_by = request.query_params.get("sort_by")
        helpers = self.get_sorting_queryset(helpers, sort_by)

        page = self.paginate_queryset(helpers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(helpers, many=True)
        return Response({
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

# Buyer/Helper List for Customer/Client===================
# ============================================================



# ============================================================
# ========Custom Offer Order Create===================
class CustomerOrderCreateViews(CreateAPIView):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    'status': True,
                    'message': 'Custom offer created!',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': error,
                },status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
# ========Custom Offer Order Create===================
# ============================================================

class CustomerOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(customer=user.customer_profile)
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Post method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

class ProviderOrderViewSet(UpdateModelViewSet):
    serializer_class = OrderSerializerAll
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(provider=user.service_provider_profile)
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                "status": True,
                "message": "Post method not allowed!"
            }, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )



