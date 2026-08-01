from config.utils import create_message_and_redirect
from django.contrib import messages
from django.shortcuts import render
from django.views import View
from django.db import IntegrityError
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

from config.utils import logout_user_from_all_devices,send_email
# Mixins are used only with Class based views, writtern first in order.
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache

from apps.users.utils import (
    get_changeEmail_key,get_register_token_key,
    get_hex_token,encode_user_id,sign_str,unsign_str,
    decode_user_id,get_website_context
)
from apps.users.models import User
from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordChangeView,
)

from .mixins import AnonymousRequiredMixin

# Views seperate the design from backend. Also it is convention to create another folder of same app 
# name inside templates to specify the exact page. another home.html will be picked if that app is 
# specified above users app, if we only did home.html

class Home(AnonymousRequiredMixin,View):
    template_name = "users/home.html"

    def get(self,request, *args, **kwargs,):
        return render(request,self.template_name,)

class Dashboard(LoginRequiredMixin,View):
    template_name = 'users/dashboard.html'

    def get(self,request, *args, **kwargs,):
        if request.htmx:
            return render(request,'users/dashboard.html#dashboard')
        return render(request,self.template_name)

class RegisterEmailView(AnonymousRequiredMixin,View):
    """
    Two step verification for email. First we only a field for column then we send an email, User clicks the url
    and redirected to register page to fill out the rest of the details. Email with secret token is sent to the user.
    """
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
        token = get_hex_token()
        # Send email
        send_email(
            email_template_name="users/register/verify_email.txt",
            html_email_template_name="users/register/verify_email.html",
            subject="Verify your email address",
            receiver= email,
            context=get_website_context(request,token=token)
        )
        # Save token in Redis after sending the email.
        value = {
            'email': email,
            'inc_TTL':False
        }
        key= get_register_token_key(token)
        cache.set(key = key, value= value,timeout=300) # TTL = 5 minutes

        return create_message_and_redirect(request=request,message='Verification link will be sent to you shortly. Kindly verify it to proceed.',url='users-home',code='success')

class CompleteRegistrationView(View):
    """
    When user clicks the register link.
    """
    # class attributes of CompleteRegsitrationView Class; if URL -> use reverse_lazy
    form_class = CompleteRegistrationForm
    template_name = 'users/register/register_user.html'
    initial  = {
            'user_type':User.UserType.STUDENT,
        }

    def get(self,request, *args, **kwargs):
        """
        GET request means user clicked the link within 5 minutes, so increase the TTL to 10 minutes 
        """

        token = kwargs["token"]
        key= get_register_token_key(token)
        val = cache.get(key)

        if not val:
            return create_message_and_redirect(request,message=f'Invalid or expired link. Kindly register again',url='register-email')

        # Update TTL, only if it is not updated once, else every reload updates the TTL
        self.initial['email'] = val['email']
        if not val['inc_TTL']:
            val['inc_TTL'] = True
            cache.set(key = key,value= val,timeout=600)

        form = self.form_class(initial = self.initial)
        return render(request,self.template_name,{'form':form})
    
    def post(self,request,*args, **kwargs):
        """
        Handle register submission. Check if the cache is still in redis.
        """
        form = self.form_class(request.POST)
        token = kwargs["token"]
        key = get_register_token_key(token)

        if not form.is_valid():
            return render(request,self.template_name,{'form':form})

        value = cache.get(key)
        if not value:
            return create_message_and_redirect(request=request,message=f'Session expired. Kindly register again',code='error',url='register-email')

        # Get email from redis
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
            # Expire immediately when the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super().form_valid(form)

class ResetPasswordView(AnonymousRequiredMixin,SuccessMessageMixin, PasswordResetView):
    """
    Here the token is created based on the existing password hash, email, pk, last login and secret key and other user info.
    So that when the linked is clicked, it becomes invalidated after one use automatically. For verification same 
    token is generated again and compared with the given token from the url.
    """
    template_name = 'users/password/reset_password.html'
    email_template_name = 'users/password/password_reset_email.txt'
    html_email_template_name = 'users/password/password_reset_email.html'
    subject_template_name = 'users/password/password_reset_subject.txt'
    success_message = "Check your email for a password reset link. If you don't receive it, please verify you are using the correct login method. Note that accounts created via OAuth (Google/Github) do not require a password."
    success_url = reverse_lazy('login')

class ResetPasswordConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    template_name = 'users/password/password_reset_confirm.html'
    success_message = "Your password has been reset."
    success_url = reverse_lazy('login')
    post_reset_login = True
    post_reset_login_backend = 'django.contrib.auth.backends.ModelBackend'

class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    success_url = reverse_lazy('users-dashboard')
    success_message = "You password has been changed successfully"

    def dispatch(self, request, *args, **kwargs):
        if request.htmx:
            self.template_name = 'Users/password/password_change.html#password-change'
        else:
            self.template_name = 'Users/password/password_change.html'

        return super().dispatch(request, *args, **kwargs)    

# Always follow early fail architecture and avoid nesting.
class UpdateProfile(LoginRequiredMixin,View):
    """
    We will send user_id<base64> signed by TimeStampSigner with salt = old_email. Redis will save the new_email
    for 5 minutes. When the link is clicked, we will identify the user from user_id<base_64>. If the link is tampered,
    wrong user's email will be fetched and used to unsign the user_id, which will result in BadSignature. If the user is
    right but the signature is being tampered, that too will be detected. Then, if the link is correct and clicked within
    5 minutes the user_id will get unsign and coverted to base64. Corresponding to that user_id, new_email stored in redis
    will be fetched and the email will be updated. We used a dynamic salt to introduce dynamic links, because signer uses 
    the secret key to sign anything. If the secret key is static, everytime the change_email link will be the same. That
    can cause security issues. We send the singature so that, the link cannot be regenerated by attackers.
    """
    form_class = UpdateUserDetailsForm
    template_name = "users/profile/profile.html"

    def get(self, request, *args, **kwargs):
        context = {
            "form": self.form_class(instance=request.user),
            "can_change_password": request.user.has_usable_password(),
        }
        if request.htmx:
            return render(request, "users/profile/profile.html#profile", context)
        return render(request, "users/profile/profile.html", context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST,request.FILES,instance=request.user,)
        # Extract old_email before form.is_valid(), otherwise after POST request; request.user.email = new_email
        old_email = request.user.email
        context = {
            "form": form,
            "can_change_password": request.user.has_usable_password(),
        }

        def get_template(request):
            if request.htmx:
                return "users/profile/profile.html#profile-form"
            return "users/profile/profile.html"

        if not form.is_valid():
            return render(request, get_template(request), context)
    
        if not form.has_changed():
            messages.error(request,f"No changes detected")
            return render(request, get_template(request), context)
        
        # Check which field has changed and save that. If Email is changed, verfication is required.
        if "email" not in form.changed_data:
            form.save()
            messages.success(request,"Profile Updated successfully")
            return render(request, get_template(request), context)

        # Social authenticated users cannot change email.
        if request.user.social_auth.exists():
            messages.error(request,f"Your email address is managed by your social account and cannot be changed.")
            return render(request, get_template(request), context)
        
        new_email = form.cleaned_data["email"]

        # If we try to submit an already taken email, either in the form or in Django Admin, it will
        # throw an error message since we defined email as unique entity, no need to check it. 
        # Flow -> ModelForm_post_clean -> instance.full_clean -> Model.validate_unique()

        # Save fields other than email
        user = form.save(commit=False)
        user.email = old_email
        user.save()

        uidb64 = encode_user_id(user_id=request.user.id)
        signed_uid = sign_str(unsigned=uidb64, salt=old_email)

        send_email(
            email_template_name="users/profile/change_email.txt",
            html_email_template_name="users/profile/change_email.html",
            subject="Verify Email Address",
            receiver=new_email,
            context= {**get_website_context(request,token=signed_uid),"user_full_name":request.user.get_full_name()}
        )
        key = get_changeEmail_key(request.user.id)
        cache.set(key=key, value={"new_email": new_email}, timeout=300)
        return create_message_and_redirect(
                request=request,
                message="Profile updated. Email has been sent to verify your new email address.",
                url="users-dashboard",
                code="success",
            )

class CompleteEmailUpdate(View):
    def get(self,request, *args, **kwargs):
        try:
            signed_uidb64 = kwargs['token']
            # The token format is value:timestamp:signature (or value:signature)
            uidb64 = signed_uidb64.split(':')[0]
            user_id = decode_user_id(uidb64)
            user = User.objects.get(id=user_id) # Fetch the user corresponding to the one given in the link.
        except (IndexError, ValueError, TypeError, User.DoesNotExist):
            return create_message_and_redirect(request=request,message='Invalid or corrupted link.',url="users-home",code='error')

        unsigned_uidb64 = unsign_str(signed=signed_uidb64, salt=user.email) # Use the link to unsign the token
        
        # If they tampered with the ID or the signature, this fails.
        if not unsigned_uidb64:
            return create_message_and_redirect(request=request,message='Invalid or corrupted link.',url="users-home",code='error')
            
        key = get_changeEmail_key(user_id=user.id)
        data = cache.get(key)
        
        if not data:
            return create_message_and_redirect(request=request,message='Link has been expired.',url="users-home",code='error')

        new_email = data['new_email']

        try:
            user.email = new_email
            user.save()
        except IntegrityError: # Throws IntegrityError if race conditions are met.
            return create_message_and_redirect(request=request,message='Email is already in use by another account.',url="users-home",code='error')

        cache.delete(key)
        
        logout_user_from_all_devices(request=request, user=user)

        messages.success(request,message='Email updated successfully. Please log in again.')
        
        return create_message_and_redirect(request,message='Email updated successfully. Please log in again.',url='login',code='success')
        