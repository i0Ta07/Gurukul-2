from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    home,
    CustomLoginView,
    dashboard,
    RegisterView,
    profile
)

urlpatterns = [
    path('', home, name='users-home'), # using app_name, we can use as <a href="{% url 'users:user-home' %}">
    path("login/", CustomLoginView.as_view(), name="login"),
    path('register/',RegisterView.as_view(), name='users-register'),
    path('logout/', LogoutView.as_view(next_page='login'),name='logout'),
    path('dashboard/',dashboard, name='users-dashboard'),
    path('profile/',profile, name='users-profile'),
]