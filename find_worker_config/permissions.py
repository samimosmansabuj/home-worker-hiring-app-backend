from rest_framework.permissions import BasePermission
from find_worker_config.model_choice import UserRole
from django.conf import settings

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.CUSTOMER

class IsServiceProvider(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.PROVIDER

class IsServicePostCustomerGetOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated and (request.user.role == UserRole.CUSTOMER or request.user.role == UserRole.PROVIDER)
        return request.user.is_authenticated and request.user.role == UserRole.PROVIDER

class IsCustomerPostServiceGetOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated and (request.user.role == UserRole.CUSTOMER or request.user.role == UserRole.PROVIDER)
        return request.user.is_authenticated and request.user.role == UserRole.CUSTOMER



class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN

class IsAuthenticatedForWrite(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated

class IsAdminWritePermissionOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == UserRole.ADMIN




class IsValidFrontendRequest(BasePermission):
    message = "You are not allowed to access this API from this client."
    def has_permission(self, request, view):
        app_key = request.headers.get("X-FRONTEND-KEY")
        origin = request.headers.get("Origin")

        print("app_key: ", app_key)
        print("origin: ", origin)
        if not app_key or not origin:
            return False
        if origin not in [
            "https://yourfrontend.com",
            "http://localhost:3000"
        ]:
            return False

        return app_key == settings.FRONTEND_APP_KEY

