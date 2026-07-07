from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TicketViewSet, AdminWalletViews, SignUpSliderViewset, CustomerScreenSlideViewset, HelperListViewset

router = DefaultRouter()
router.register(r"tickets", TicketViewSet, basename="ticket")

site_router = DefaultRouter()
site_router.register(r"signup-slide", SignUpSliderViewset, basename="site-signup-slide")
site_router.register(r"customer-screen", CustomerScreenSlideViewset, basename="customer-screen")

# ============================================================================================================
site_router.register(r"helper", HelperListViewset, basename="helper")
# ============================================================================================================


# ============================================================================================================
from .admin_views import AdminAuthViews, AdminUserViews, AdminProviderViews, AdminCustomerViews, DashboardAPIView, AdminOrderViewSet, PaymentTransactionViewSets, OrderRefundViewSets

admin_route = DefaultRouter()
admin_route.register(r"user", AdminUserViews, basename="admin-user")
admin_route.register(r"provider", AdminProviderViews, basename="provider-profile")
admin_route.register(r"customer", AdminCustomerViews, basename="customer-profile")
admin_route.register(r"order", AdminOrderViewSet, basename="admin-side-order")
admin_route.register(r"payment-transaction", PaymentTransactionViewSets, basename="admin-payment-transaction")
admin_route.register(r"order-refund", OrderRefundViewSets, basename="order-refund")
# ============================================================================================================

urlpatterns = [
    # Ticket========================================
    path("", include(router.urls)),

    # Site Settings========================================
    path("", include(site_router.urls)),

    path("core/admin-wallet/", AdminWalletViews.as_view(), name="admin-wallet"),
    
    # Admin Views===============================================
    path("admin/token/auth/", AdminAuthViews.as_view(), name="admin-login"),
    path("dashboard/", DashboardAPIView.as_view(), name="admin-dashboard"),
    path("admin/", include(admin_route.urls)),
]

