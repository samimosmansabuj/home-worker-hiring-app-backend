from django.contrib import admin
from django.urls import path, include, re_path
from account.views import WelComeAPI
from django.conf import settings
from django.views.static import serve as static_serve
from dotenv import load_dotenv
load_dotenv()
import os

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


admin.site.site_title = "HomeWorkerFinder"
admin.site.site_header = "HomeWorkerFinder"
admin.site.app_index = "Welcome to Home Worker Finder"

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", WelComeAPI.as_view(), name="WelcomeAPI"),

    # include APP Urls File==========
    path("api/v1/", include("account.urls")),
    path("api/v1/", include("chat_notify.urls")),
    path("api/v1/", include("core.urls")),
    
    # remove after complete job app-----
    path("api/v1/", include("task.urls")),
    

    # API schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # Redoc UI
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

SERVE_MEDIA = os.getenv("SERVE_MEDIA", "False").strip().lower() in ("true","1","yes")

if SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', static_serve, {'document_root': settings.STATIC_ROOT}),
    ]
