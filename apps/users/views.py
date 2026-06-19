from django.shortcuts import render,redirect
from django.contrib import messages
from django.views import View
from django.urls import reverse_lazy
from .forms import RegisterForm,LoginForm

# Mixins are used only with Class based views, writtern first in order.
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required

from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordChangeView,
)
# Views seperate the design from backend. Also it is convention to create another folder of same app name inside templates
# to specify the exact page. another home.html will be picked if that app is specified above users app, if we only did home.html

def home(request):
    return render(request, 'users/home.html')

@login_required 
def dashboard(request):
    return render(request,'users/dashboard.html')

@login_required
def profile(request):
    return render(request,'users/profile.html')

class RegisterView(View):
    form_class = RegisterForm
    initial = {
        'key':'value'
    }
    template_name = 'users/register.html'
    

    def get(self,request, *args, **kwargs):
        form = self.form_class(initial = self.initial)
        return render(request,self.template_name,{'form':form})
    
    def post(self,request,*args,**kwargs):
        form  = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,f'Account created successfully')
            return redirect(to=reverse_lazy("login"))
        
        return render(request, self.template_name, {'form': form})
    
    # Dispatch is traffic controller. Request goes to dispatch check if post -> call post; if get-> call get; earliest convenient hook in a Class based view
    def dispatch(self, request, *args, **kwargs):
        # will redirect to the dashboard page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to=reverse_lazy("users-dashboard"))

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = "users/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy('users-dashboard')

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")
        if not remember_me:
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super().form_valid(form)

class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/reset-password.html'
    email_template_name = 'users/password_reset_email.txt'
    html_email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_message = "If the email is registered with us, you'll receive a password reset link shortly."
    success_url = reverse_lazy('login')

class ResetPasswordConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_message = "Your password has been reset."
    success_url = reverse_lazy('login')

class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'Users/password_change.html'
    success_url = reverse_lazy('users-dashboard')
    success_message = "You password has been changed successfully"

    