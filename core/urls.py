from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TicketViewSet, AdminWalletViews, SignUpSliderViewset, CustomerScreenSlideViewset

router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="ticket")

site_router = DefaultRouter()
site_router.register(r"signup-slide", SignUpSliderViewset, basename="site-signup-slide")
site_router.register(r"customer-screen", CustomerScreenSlideViewset, basename="customer-screen")

urlpatterns = [
    # Ticket========================================
    path("", include(router.urls)),

    # Site Settings========================================
    path("", include(site_router.urls)),

    path("core/admin-wallet/", AdminWalletViews.as_view(), name="admin-wallet")
]

