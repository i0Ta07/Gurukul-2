from typing import Literal

from django.shortcuts import render,redirect
from django.contrib import messages
from django.views import View
# Django reads your views.py file before it reads your urls.py file. It doesn't know your URL names yet. 
# Inside a view if you put reverse('home'). It will try to find, but it cannot find it and throws an error.
#  Hence use reverse_lazy in Class-Level Attribute.

# If you are indented inside a def, use reverse(). If you are writing a line directly under a class
#  (not inside a method), use reverse_lazy(). Functions doesn't run as soon as website start.
from django.urls import  reverse_lazy
from .forms import (
    LoginForm,
    RegisterEmailForm,
    CompleteRegistrationForm,
    UpdateUserDetailsForm,
)

from django.http import HttpResponseNotAllowed

# Mixins are used only with Class based views, writtern first in order.
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.cache import cache

from django.contrib.sites.shortcuts import get_current_site
import secrets

from django.template.loader import render_to_string
from .models import User

# Base 64 encoding 
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

# Session
from .models import CustomSession
from django.contrib.auth import logout

from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordChangeView,
)

from .tasks import send_email_task

# Views seperate the design from backend. Also it is convention to create another folder of same app 
# name inside templates to specify the exact page. another home.html will be picked if that app is 
# specified above users app, if we only did home.html

def home(request):
    return render(request, 'users/home.html')

@login_required 
def dashboard(request):
    return render(request,'users/dashboard.html')

def send_email(request,email_template_name,html_email_template_name,subject,receiver,token):
    """
    Adds the send_email task to redis task queue.
    """
    
    current_site = get_current_site(request)
    domain = current_site.domain
    protocol = 'https' if request.is_secure() else 'http'
    
    extra_email_context = {
        'domain':domain,
        'token':token,
        'protocol':protocol,
    }
    
    text_content = render_to_string(
        email_template_name,
        context=extra_email_context,
    )

    html_content = render_to_string(
        html_email_template_name,
        context=extra_email_context,
    )

    send_email_task.delay(subject,text_content,receiver,html_content)

def get_register_token_key(token):
    return f'register:token:{token}'

def get_token():
    return secrets.token_hex(32)

def create_message_and_redirect(request, message: str, url: str, code: Literal['info', 'success', 'error', 'warning'] = 'error'):
    """Create the message and redirects to the given URL"""
    # Dynamically get the correct messages function based on the 'code' string
    message_func = getattr(messages, code)
    message_func(request, message)
    
    return redirect(url)

class RegisterEmailView(View):
    form_class = RegisterEmailForm
    template_name = 'users/register/register_email.html'

    def get(self,request, *args, **kwargs):
        form = self.form_class()
        return render(request,self.template_name,{'form':form})
    
    def post(self,request,*args, **kwargs):
        form = self.form_class(request.POST)
        if not form.is_valid():
            return render(request,self.template_name,{'form':form})

        email = form.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            return create_message_and_redirect(request=request,message='Account already exists. Kindly login', url='login',code='error')
        # Generate token 
        token = get_token()
        # Send email
        send_email(
            request=request,
            email_template_name="users/register/verify_email.txt",
            html_email_template_name="users/register/verify_email.html",
            subject="Verify your email address",
            receiver= email,
            token = token
        )
        # Save token in Redis after sending the email.
        value = {
            'email': email,
        }
        key= get_register_token_key(token)
        cache.set(key = key, value= value,timeout=300) # 5 minutes

        return create_message_and_redirect(request=request,message='Verification link will be sent to you shortly. Kindly verify it to proceed.',url='users-home',code='success')

    
    # Dispatch is traffic controller. Request goes to dispatch check if post -> call post; if get-> call get; earliest convenient hook in a Class based view
    def dispatch(self, request, *args, **kwargs):
        # will redirect to the dashboard page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect("users-dashboard")

        # else process dispatch as it otherwise normally would
        return super(RegisterEmailView, self).dispatch(request, *args, **kwargs)    

class CompleteRegistrationView(View):
    # class attributes of CompleteRegsitrationView Class; if URL -> use reverse_lazy
    form_class = CompleteRegistrationForm
    template_name = 'users/register/register_user.html'
    initial  = {
        'user_type':User.UserType.STUDENT
    }
    
    def get(self,request, *args, **kwargs):
        token = kwargs["token"]
        form = self.form_class(initial = self.initial)
        # Increase the TTL to 5 minutes
        key = get_register_token_key(token)
        if cache.touch(key,timeout=900):
            return render(request,self.template_name,{'form':form})
        else:
            messages.error(request,f'Invalid or expired link. Kindly register again')
            return redirect('register-email')
    
    def post(self,request,*args, **kwargs):
        form = self.form_class(request.POST)
        token = kwargs["token"]
        key = get_register_token_key(token)

        if not form.is_valid():
            return render(request,self.template_name,{'form':form})

        value = cache.get(key)
        if not value:
            return create_message_and_redirect(request=request,message=f'Session expired. Kindly register again',code='error',url='register-email')

        email = value['email']
        user = form.save(commit=False) # form.save; model.forms special fucntion to form attributes inside db for the selected model
        user.email = email
        user.save()

        # Delete key after successfult user creation
        cache.delete(key)
        return create_message_and_redirect(request=request,message=f'Account created successfully',code='success',url='login')

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
    template_name = 'users/password/reset_password.html'
    email_template_name = 'users/password/password_reset_email.txt'
    html_email_template_name = 'users/password/password_reset_email.html'
    subject_template_name = 'users/password/password_reset_subject.txt'
    success_message = "If the email is registered with us, you'll receive a password reset link shortly."
    success_url = reverse_lazy('login')

class ResetPasswordConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'users/password/password_reset_confirm.html'
    success_message = "Your password has been reset."
    success_url = reverse_lazy('login')
    subject_template_name = 'Gurukul Password Reset'

class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'Users/password/password_change.html'
    success_url = reverse_lazy('users-dashboard')
    success_message = "You password has been changed successfully"

def encode_user_id(user_id: int) -> str:
    """Converts an integer user_id to a URL-safe base64 string."""
    return urlsafe_base64_encode(force_bytes(user_id))

def decode_user_id(encoded_id: str) -> int:
    """Decodes a URL-safe base64 string back to an integer user_id."""
    return int(force_str(urlsafe_base64_decode(encoded_id)))

# Use the old email as salt
def get_signer(salt):
    return TimestampSigner(salt=salt)

def sign_str(unsigned:str,salt:str):
    signer = get_signer(salt=salt)
    value = signer.sign(unsigned)
    return value

def unsign_str(signed:str,salt:str,max_age= 300):
    signer = get_signer(salt=salt)
    try:
        value = signer.unsign(signed,max_age=max_age)
    except (SignatureExpired, BadSignature):
        return False
    return value

def get_changeEmail_key(user_id):
    return f'change_email:user:{user_id}'


# Always follow early fail architecture and avoid nesting.
class UpdateProfile(LoginRequiredMixin,View):
    """
    View to update profile details. If email is changed
    a verification link is sent to the new email. When clicked
    then only it is changed. The user.id is signed with old_email
    to introduce dynamic signed strings. Redis is used to save
    the new_email for 5 minutes.
    """
    form_class = UpdateUserDetailsForm
    template_name = "users/profile/profile.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": self.form_class(instance=request.user)})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST,request.FILES,instance=request.user,)
        # Extract old_email before form.is_valid(), otherwise after POST request; request.user.email = new_email
        old_email = request.user.email

        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
    
        if not form.has_changed():
            return create_message_and_redirect(
                request=request,
                message="No changes were made",
                url="users-dashboard",
                code="info",
            )
        
        # Check which field has changed and save that. If Email is changed, verfication is required.
        if "email" not in form.changed_data:
            form.save()
            messages.success(request=request,message="Profile updated successfully")
            return render(request, self.template_name, {"form": form})

        # Social authenticated users cannot change email.
        if request.user.social_auth.exists():
            return create_message_and_redirect(
                request=request,
                message="Your email address is managed by your social account and cannot be changed.",
                url="users-dashboard",
                code="error",
            )
        
        new_email = form.cleaned_data["email"]

        if User.objects.filter(email=new_email).exists():
            messages.error(request=request,message="Email already taken. Failed to save changes")
            return render(request, self.template_name, {"form": form})

        # Save fields other than email
        user = form.save(commit=False)
        user.email = old_email
        user.save()

        uidb64 = encode_user_id(user_id=request.user.id)
        signed_uid = sign_str(unsigned=uidb64, salt=old_email)

        send_email(
            request=request,
            email_template_name="users/profile/change_email.txt",
            html_email_template_name="users/profile/change_email.html",
            subject="Verify Email Address",
            receiver=new_email,
            token=signed_uid,
        )
        key = get_changeEmail_key(request.user.id)
        cache.set(key=key, value={"new_email": new_email}, timeout=300)
        messages.warning(
            request,
            "Profile updated. Email has been sent to verify your new email address.",
        )
        return redirect("users-dashboard")



def logout_user_from_all_devices(request, user):
    """
    Instantly deletes all active sessions for the user at the database level.
    """
    # Flush all sessions stored in database for the current user
    CustomSession.objects.filter(user_id=user.id).delete()
    
    # Clear the cookie/session for the current request context
    logout(request)

def CompleteEmailUpdate(request,token):
    """
    Extract the user_id from unsafe link. Use it to retrieve the salt
    If tampered, the salt = old_email will be incorrect, and during .unsign(),
    we will get a bad singature. Hence, the request will be invalidated.
    """
    if request.method != 'GET':
        return HttpResponseNotAllowed(["GET"])

    try:
        signed_uidb64 = token
        # The token format is value:timestamp:signature (or value:signature)
        uidb64 = signed_uidb64.split(':')[0]
        user_id = decode_user_id(uidb64)
        user = User.objects.get(id=user_id)
    except (IndexError, ValueError, TypeError, User.DoesNotExist):
        return create_message_and_redirect(request=request,message='Invalid or corrupted link.',url="users-home",code='error')

    unsigned_uidb64 = unsign_str(signed=signed_uidb64, salt=user.email)
    
    if not unsigned_uidb64:
        return create_message_and_redirect(request=request,message='Invalid or expired link.',url="users-home",code='error')
        
    key = get_changeEmail_key(user_id=user.id)
    data = cache.get(key)
    
    if not data:
        return create_message_and_redirect(request=request,message='Link has expired or already been used.',url="users-home",code='error')

    new_email = data['new_email']
    
    if User.objects.filter(email=new_email).exists():
        return create_message_and_redirect(request=request,message='Email is already in use by another account.',url="users-home",code='error')

    user.email = new_email
    user.save() 
    
    cache.delete(key)
    
    logout_user_from_all_devices(request=request, user=user)
    
    messages.success(request, 'Email updated successfully. Please log in again.')
    return render(request=request,template_name='users/profile/update_email_complete.html')
    
