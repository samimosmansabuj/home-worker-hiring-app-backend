from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, OrderViewSets


router = DefaultRouter()
router.register("categories", ServiceCategoryViewSet, basename="categories")
router.register("order", OrderViewSets, basename="orders")
# router.register("tasks", ServiceTaskViewSet, basename="tasks")
# router.register("prototypes", ServicePrototypeViewSet, basename="prototypes")
# router.register("job-requests", TaskRequestViewSet, basename="job-requests")

# user_router = DefaultRouter()
# user_router.register("tasks", ServiceTaskViewSet, basename="tasks")

urlpatterns = [
    path("", include(router.urls)),
    # path("user/", include(user_router.urls))
]

