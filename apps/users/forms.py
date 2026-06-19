
from django import forms
# from django.contrib.auth.models import User
from .models import User
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import SplitPhoneNumberField
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm

class BootstrapSplitPhoneNumberField(SplitPhoneNumberField):
    def prefix_field(self):
        field = super().prefix_field()
        field.widget.attrs.update({
            'class': 'form-select w-50',
        })
        return field

    def number_field(self):
        field = super().number_field()
        field.widget.attrs.update({
            'class': 'form-control',
            'placeholder': '10 digit number',
        })
        return field
    

# Nobody wants to give DOB and phone number during registration. Add them in profile.
class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('First Name'),
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder':'John'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder':'Doe'}),
    )
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control','placeholder':'john_doe@example.com'}),
    )
    # phone_number = BootstrapSplitPhoneNumberField(
    #     region='IN',
    #     label=_('Phone Number'),
    #     required=False,
    # )
    user_type = forms.ChoiceField(
        choices=User.UserType,
        label=_('User Type'),
        required=True,
        initial=User.UserType.STUDENT,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    # date_of_birth = forms.DateField(
    #     label=_('Date of Birth'),
    #     widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    #     required=False
    # )
    password1 = forms.CharField(max_length=20,
        label=_('Password'),
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'data-toggle': 'password','id': 'password'
            })
        )
    
    password2 = forms.CharField(
        label=_('Confirm Password'),
        max_length=20,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'data-toggle': 'password','id': 'password'
            })
        )
    
    # BootstrapSplitPhoneNumberField store '' instead of Null. So, predefined clean function for devs by django, called automatically.
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if not phone:
            return None
        return phone
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'password1', 'password2', 'user_type',
        ]
    

class LoginForm(AuthenticationForm):
    # Django AuthenticationForm still requires the name as username but since we did USERNAME_FIELD = "email", it will get replace
    username = forms.EmailField(max_length=100,label=_('Email') ,required=True,widget=forms.EmailInput(attrs={
        'placeholder': 'john_doe@gmail.com',
        'class': 'form-control'
        })
    )
    
    password = forms.CharField(max_length=50,required=True,widget=forms.PasswordInput(attrs={
        'placeholder': 'Password',
        'class': 'form-control','data-toggle': 'password',
        'id': 'password','name': 'password'
        })
    )
    remember_me = forms.BooleanField(required=False)
    class Meta:
        model = User
        fields = ['username', 'password', 'remember_me']


        