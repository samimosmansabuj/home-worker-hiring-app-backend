from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import HelperListViewset, CustomerOrderCreateViews, CustomerOrderViewSet, ProviderOrderViewSet


# ============================================================================================================
site_router = DefaultRouter()
site_router.register(r"helper", HelperListViewset, basename="helper")
# ============================================================================================================

# ============================================================================================================
order_router = DefaultRouter()
order_router.register(r"customer-list", CustomerOrderViewSet, basename="customer-order")
order_router.register(r"provider-list", ProviderOrderViewSet, basename="provider-order")
# ============================================================================================================

urlpatterns = [
    path("site/", include(site_router.urls)),
    
    path("order-create/", CustomerOrderCreateViews.as_view(), name="order-create"),
    path("order/", include(order_router.urls)),
]

