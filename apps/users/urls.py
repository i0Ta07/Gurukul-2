from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    home,
    CustomLoginView,
    dashboard,
    RegisterEmailView,
    CompleteRegistrationView,
    UpdateProfile,
    CompleteEmailUpdate
)

urlpatterns = [
    path('', home, name='users-home'), # using app_name, we can use as <a href="{% url 'users:user-home' %}">
    path("login/", CustomLoginView.as_view(), name="login"),
    path('logout/', LogoutView.as_view(next_page='login'),name='logout'),
    path('dashboard/',dashboard, name='users-dashboard'),
    path('profile/',UpdateProfile.as_view(), name='users-profile'),
    path('verify-email/<str:token>',CompleteEmailUpdate, name='verify-email'),
    path('register-email/',view = RegisterEmailView.as_view(),name= 'register-email'),
    path('register/complete/<str:token>/',view = CompleteRegistrationView.as_view(), name= 'complete-register-token'),
]