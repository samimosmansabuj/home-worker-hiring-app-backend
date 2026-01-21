"""
URL configuration for find_worker_config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from account.views import WelComeAPI

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", WelComeAPI.as_view(), name="WelcomeAPI"),

    # include APP Urls File==========
    path("api/v1/", include("account.urls")),
    path("api/v1/", include("chat_notify.urls")),
    path("api/v1/", include("order.urls")),
    path("api/v1/", include("task.urls")),
    path("api/v1/", include("wallet.urls")),
]
