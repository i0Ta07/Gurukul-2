"""
URL configuration for config project.

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
from django.urls import path,include

from apps.users.views import (
    ResetPasswordView,
    ResetPasswordConfirmView,
    ChangePasswordView
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("social/", include('social_django.urls', namespace="social")),

    # Apps
    path("", include("apps.users.urls")),
    path("orgs/", include("apps.orgs.urls")),
    path("classes/", include("apps.classes.urls")),
    
    # Password
    path('reset-password/',ResetPasswordView.as_view(),name='reset-password'),
    
    # uidb64 = userid base 64 and password recovery token. Both were sent in the mail
    path('password-reset-confirm/<str:uidb64>/<str:token>/',ResetPasswordConfirmView.as_view(), name='password-reset-confirm'),
    path('password-change/',ChangePasswordView.as_view(), name='password-change'),

    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# above static maps the MEDIA_URL to MEDIA_ROOT; do not use in prod
