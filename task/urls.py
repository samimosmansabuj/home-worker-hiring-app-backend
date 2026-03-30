from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ServiceSubCategoryViewSet, ReviewAndRatingViewSets, CustomerOrderViewSet, ProviderOrderViewSet, AdminOrderViewSet, PaymentTransactionViewSets, OrderRefundViewSets


router = DefaultRouter()
# For Categories Section-------
router.register(r"category", ServiceCategoryViewSet, basename="category")
router.register(r"sub-category", ServiceSubCategoryViewSet, basename="sub-category")
# For Order Section--------
router.register(r"customer/order", CustomerOrderViewSet, basename="customer_orders")
router.register(r"provider/order", ProviderOrderViewSet, basename="provider_orders")
router.register(r"admin/order", AdminOrderViewSet, basename="admin_orders")
# For Review Section---------
router.register(r"review", ReviewAndRatingViewSets, basename="reviews")
# For Payment Transaction Section---------
router.register(r"payment-transaction", PaymentTransactionViewSets, basename="payment-transaction")
router.register(r"order-refund", OrderRefundViewSets, basename="order-refund")

urlpatterns = [
    path("", include(router.urls)),
    # path("", include(router.urls)),
]

