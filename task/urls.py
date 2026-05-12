from django.urls import path, include
from .views import ServiceCategoryViewSet, ServiceSubCategoryViewSet, ReviewAndRatingViewSets, CustomerOrderViewSet, ProviderOrderViewSet, AdminOrderViewSet, PaymentTransactionViewSets, OrderRefundViewSets, CustomerOrderCreateViews, CustomerOrderViewSet, ProviderOrderViewSet
from rest_framework.routers import DefaultRouter



router = DefaultRouter()
# For Categories Section-------
router.register(r"category", ServiceCategoryViewSet, basename="category")
router.register(r"sub-category", ServiceSubCategoryViewSet, basename="sub-category")
# For Order Section--------

order_router = DefaultRouter()
order_router.register(r"customer", CustomerOrderViewSet, basename="customer-order")
order_router.register(r"provider", ProviderOrderViewSet, basename="provider-order")
order_router.register(r"admin", AdminOrderViewSet, basename="admin_orders")

# For Review Section---------
router.register(r"review", ReviewAndRatingViewSets, basename="reviews")
# For Payment Transaction Section---------
router.register(r"payment-transaction", PaymentTransactionViewSets, basename="payment-transaction")
router.register(r"order-refund", OrderRefundViewSets, basename="order-refund")

urlpatterns = [
    path("", include(router.urls)),
    
    path("order-create/", CustomerOrderCreateViews.as_view(), name="order-create"),
    path("order/", include(order_router.urls)),
]

