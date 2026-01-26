from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ReviewAndRatingViewSets, CustomerOrderViewSet, ProviderOrderViewSet, AdminOrderViewSet


router = DefaultRouter()
router.register(r"categories", ServiceCategoryViewSet, basename="categories")
# router.register(r"order", OrderViewSets, basename="orders")
router.register(r"customer/order", CustomerOrderViewSet, basename="customer_orders")
router.register(r"provider/order", ProviderOrderViewSet, basename="provider_orders")
router.register(r"admin/order", AdminOrderViewSet, basename="admin_orders")
router.register(r"review", ReviewAndRatingViewSets, basename="reviews")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(router.urls)),
]

