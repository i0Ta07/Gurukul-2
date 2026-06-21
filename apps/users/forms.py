
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
            'class': 'form-select w-50 mb-3',
        })
        return field

    def number_field(self):
        field = super().number_field()
        field.widget.attrs.update({
            'class': 'form-control w-75',
            'placeholder': '10 digit number',
        })
        return field
    

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


class RegisterEmailForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control','placeholder':'john_doe@example.com'}),
    )

class CompleteRegistrationForm(UserCreationForm):
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
    user_type = forms.ChoiceField(
        choices=User.UserType,
        label=_('User Type'),
        required=True,
        # initial=User.UserType.STUDENT,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

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
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name','user_type',
            'password1', 'password2',
        ]

class UpdateUserDetailsForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('First Name'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    user_type = forms.ChoiceField(
        choices=User.UserType,
        label=_('User Type'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    phone_number = BootstrapSplitPhoneNumberField(
        region='IN',
        label=_('Phone Number'),
        required=False,
    )
    date_of_birth = forms.DateField(
        label=_('Date of Birth'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    profile_photo = forms.ImageField(widget=forms.FileInput(attrs={'class': 'form-control-file'}),required=False)
    bio = forms.CharField(max_length=100,label=_('Bio'),widget=forms.TextInput(attrs={'class': 'form-control','placeholder':'About you'}),required=False)

    # BootstrapSplitPhoneNumberField store '' instead of Null. So, predefined clean function for devs by django, called automatically.
    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        if not phone:
            return None
        return phone
    
    class Meta:
        model = User
        fields = ['first_name','last_name','email','user_type','phone_number','date_of_birth','profile_photo','bio']